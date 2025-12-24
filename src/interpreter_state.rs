// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2018-2025)

//! Per-interpreter state management for subinterpreter support.
//!
//! This module manages interpreter-specific state to support Python 3.14 subinterpreters.
//! Each interpreter has its own instance of all PyObject pointers and caches.

use core::ffi::CStr;
use core::ptr::null_mut;
use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use crate::deserialize::cache::KeyCache;
use crate::ffi::{
    Py_DECREF, Py_INCREF, Py_XDECREF, PyErr_NewException, PyExc_TypeError, PyImport_ImportModule,
    PyMapping_GetItemString, PyObject, PyObject_GenericGetDict, PyTypeObject,
    PyUnicode_InternFromString, PyUnicode_New, orjson_fragmenttype_new,
};

/// Per-interpreter state containing all interpreter-specific PyObject pointers and caches.
/// This struct is Send + Sync because:
/// - PyObject pointers are only accessed when the GIL is held (single-threaded within interpreter)
/// - The HashMap is protected by a Mutex
/// - UnsafeCell for key_map is safe because GIL ensures single-threaded access
unsafe impl Send for InterpreterState {}
unsafe impl Sync for InterpreterState {}

/// Pre-allocated buffer for yyjson parsing to avoid malloc/free overhead
/// Uses a simple pool with configurable size tiers
pub(crate) struct ParseBuffer {
    pub ptr: *mut core::ffi::c_void,
    pub capacity: usize,
}

impl ParseBuffer {
    pub fn new() -> Self {
        ParseBuffer {
            ptr: null_mut(),
            capacity: 0,
        }
    }

    /// Ensure buffer has at least the required capacity
    /// Returns the buffer pointer and actual capacity
    #[inline]
    pub unsafe fn ensure_capacity(&mut self, required: usize) -> (*mut core::ffi::c_void, usize) {
        unsafe {
            if self.capacity >= required {
                (self.ptr, self.capacity)
            } else {
                // Free old buffer if exists
                if !self.ptr.is_null() {
                    crate::ffi::PyMem_Free(self.ptr);
                }
                // Allocate new buffer with some headroom (round up to next power of 2 or 4KB minimum)
                let new_capacity = required.next_power_of_two().max(4096);
                let new_ptr = crate::ffi::PyMem_Malloc(new_capacity);
                self.ptr = new_ptr;
                self.capacity = if new_ptr.is_null() { 0 } else { new_capacity };
                (self.ptr, self.capacity)
            }
        }
    }
}

impl Drop for ParseBuffer {
    fn drop(&mut self) {
        if !self.ptr.is_null() {
            unsafe { crate::ffi::PyMem_Free(self.ptr) };
        }
    }
}

/// Slimmed-down per-interpreter state.
///
/// Built-in types (str, int, dict, list, etc.) are now accessed via direct
/// CPython global symbols in typeref.rs, eliminating pointer indirection.
/// Only truly per-interpreter data is stored here.
pub(crate) struct InterpreterState {
    // Keyword argument strings (interned per-interpreter)
    pub default: *mut PyObject,
    pub option: *mut PyObject,

    // Empty string singleton (per-interpreter)
    pub empty_unicode: *mut PyObject,

    // Type objects that must be looked up dynamically (per-interpreter)
    // These come from external modules and may differ between interpreters
    pub datetime_type: *mut PyTypeObject,
    pub date_type: *mut PyTypeObject,
    pub time_type: *mut PyTypeObject,
    pub uuid_type: *mut PyTypeObject,
    pub enum_type: *mut PyTypeObject,
    pub field_type: *mut PyTypeObject,
    pub fragment_type: *mut PyTypeObject,
    pub zoneinfo_type: *mut PyTypeObject,

    // Interned strings (per-interpreter)
    pub utcoffset_method_str: *mut PyObject,
    pub normalize_method_str: *mut PyObject,
    pub convert_method_str: *mut PyObject,
    pub dst_str: *mut PyObject,
    pub dict_str: *mut PyObject,
    pub dataclass_fields_str: *mut PyObject,
    pub slots_str: *mut PyObject,
    pub field_type_str: *mut PyObject,
    pub array_struct_str: *mut PyObject,
    pub dtype_str: *mut PyObject,
    pub descr_str: *mut PyObject,
    pub value_str: *mut PyObject,
    pub int_attr_str: *mut PyObject,

    // Exception types (per-interpreter)
    pub json_encode_error: *mut PyObject,
    pub json_decode_error: *mut PyObject,

    // Cache - per-interpreter (using UnsafeCell for interior mutability)
    // Safe because GIL ensures single-threaded access within an interpreter
    // Boxed to avoid 48KB stack allocation when creating InterpreterState
    #[cfg(not(Py_GIL_DISABLED))]
    pub key_map: core::cell::UnsafeCell<Box<KeyCache>>,

    // Pre-allocated buffer for yyjson parsing - avoids malloc/free per parse
    // Safe because GIL ensures single-threaded access
    pub parse_buffer: core::cell::UnsafeCell<ParseBuffer>,
}

unsafe fn look_up_type_object(module_name: &CStr, member_name: &CStr) -> *mut PyTypeObject {
    unsafe {
        let module = PyImport_ImportModule(module_name.as_ptr());
        let module_dict = PyObject_GenericGetDict(module, null_mut());
        let ptr = PyMapping_GetItemString(module_dict, member_name.as_ptr()).cast::<PyTypeObject>();
        Py_DECREF(module_dict);
        Py_DECREF(module);
        ptr
    }
}

#[cfg(not(PyPy))]
unsafe fn look_up_datetime(
    datetime_type: &mut *mut PyTypeObject,
    date_type: &mut *mut PyTypeObject,
    time_type: &mut *mut PyTypeObject,
    zoneinfo_type: &mut *mut PyTypeObject,
) {
    unsafe {
        crate::ffi::PyDateTime_IMPORT();
        let datetime_capsule = crate::ffi::PyCapsule_Import(c"datetime.datetime_CAPI".as_ptr(), 1)
            .cast::<crate::ffi::PyDateTime_CAPI>();
        debug_assert!(!datetime_capsule.is_null());

        *datetime_type = (*datetime_capsule).DateTimeType;
        *date_type = (*datetime_capsule).DateType;
        *time_type = (*datetime_capsule).TimeType;
        *zoneinfo_type = (*datetime_capsule).TZInfoType;
    }
}

#[cfg(PyPy)]
unsafe fn look_up_datetime(
    datetime_type: &mut *mut PyTypeObject,
    date_type: &mut *mut PyTypeObject,
    time_type: &mut *mut PyTypeObject,
    zoneinfo_type: &mut *mut PyTypeObject,
) {
    unsafe {
        *datetime_type = look_up_type_object(c"datetime", c"datetime");
        *date_type = look_up_type_object(c"datetime", c"date");
        *time_type = look_up_type_object(c"datetime", c"time");
        *zoneinfo_type = look_up_type_object(c"zoneinfo", c"ZoneInfo");
    }
}

impl InterpreterState {
    /// Initialize a new interpreter state for the current interpreter.
    ///
    /// This is a cold path - only called once per interpreter.
    /// Built-in types are now accessed via direct CPython globals,
    /// so we only initialize per-interpreter specific data here.
    #[cold]
    #[cfg_attr(feature = "optimize", optimize(size))]
    pub(crate) unsafe fn new() -> Self {
        unsafe {
            debug_assert!(crate::opt::MAX_OPT < i32::from(u16::MAX));

            let mut state = InterpreterState {
                default: null_mut(),
                option: null_mut(),
                empty_unicode: PyUnicode_New(0, 255),
                // Dynamic types - looked up from external modules
                datetime_type: null_mut(),
                date_type: null_mut(),
                time_type: null_mut(),
                uuid_type: null_mut(),
                enum_type: null_mut(),
                field_type: null_mut(),
                fragment_type: null_mut(),
                zoneinfo_type: null_mut(),
                // Interned strings
                utcoffset_method_str: null_mut(),
                normalize_method_str: null_mut(),
                convert_method_str: null_mut(),
                dst_str: null_mut(),
                dict_str: null_mut(),
                dataclass_fields_str: null_mut(),
                slots_str: null_mut(),
                field_type_str: null_mut(),
                array_struct_str: null_mut(),
                dtype_str: null_mut(),
                descr_str: null_mut(),
                value_str: null_mut(),
                int_attr_str: null_mut(),
                // Exceptions
                json_encode_error: null_mut(),
                json_decode_error: null_mut(),
                // Caches - Box to avoid 48KB stack allocation
                #[cfg(not(Py_GIL_DISABLED))]
                key_map: core::cell::UnsafeCell::new(Box::new(KeyCache::new())),
                parse_buffer: core::cell::UnsafeCell::new(ParseBuffer::new()),
            };

            // Look up types from external modules
            look_up_datetime(
                &mut state.datetime_type,
                &mut state.date_type,
                &mut state.time_type,
                &mut state.zoneinfo_type,
            );

            state.uuid_type = look_up_type_object(c"uuid", c"UUID");
            state.enum_type = look_up_type_object(c"enum", c"EnumMeta");
            state.field_type = look_up_type_object(c"dataclasses", c"_FIELD");

            state.fragment_type = orjson_fragmenttype_new();

            state.int_attr_str = PyUnicode_InternFromString(c"int".as_ptr());
            state.utcoffset_method_str = PyUnicode_InternFromString(c"utcoffset".as_ptr());
            state.normalize_method_str = PyUnicode_InternFromString(c"normalize".as_ptr());
            state.convert_method_str = PyUnicode_InternFromString(c"convert".as_ptr());
            state.dst_str = PyUnicode_InternFromString(c"dst".as_ptr());
            state.dict_str = PyUnicode_InternFromString(c"__dict__".as_ptr());
            state.dataclass_fields_str =
                PyUnicode_InternFromString(c"__dataclass_fields__".as_ptr());
            state.slots_str = PyUnicode_InternFromString(c"__slots__".as_ptr());
            state.field_type_str = PyUnicode_InternFromString(c"_field_type".as_ptr());
            state.array_struct_str = PyUnicode_InternFromString(c"__array_struct__".as_ptr());
            state.dtype_str = PyUnicode_InternFromString(c"dtype".as_ptr());
            state.descr_str = PyUnicode_InternFromString(c"descr".as_ptr());
            state.value_str = PyUnicode_InternFromString(c"value".as_ptr());
            state.default = PyUnicode_InternFromString(c"default".as_ptr());
            state.option = PyUnicode_InternFromString(c"option".as_ptr());

            state.json_encode_error = PyExc_TypeError;
            Py_INCREF(state.json_encode_error);
            let json_jsondecodeerror =
                look_up_type_object(c"json", c"JSONDecodeError").cast::<PyObject>();
            debug_assert!(!json_jsondecodeerror.is_null());
            state.json_decode_error = PyErr_NewException(
                c"hyperjson.JSONDecodeError".as_ptr(),
                json_jsondecodeerror,
                null_mut(),
            );
            debug_assert!(!state.json_decode_error.is_null());
            Py_XDECREF(json_jsondecodeerror);

            state
        }
    }
}

/// Global registry of interpreter states, keyed by module pointer (as usize for Send+Sync).
/// Each interpreter has its own module instance, so we use the module pointer as the key.
/// Using usize is safe because we only compare pointers, never dereference them.
static INTERPRETER_STATES: OnceLock<Mutex<HashMap<usize, Box<InterpreterState>>>> = OnceLock::new();

/// Get or create the interpreter state for the given module.
/// The module pointer uniquely identifies the interpreter.
#[inline(always)]
pub(crate) unsafe fn get_or_init_state(module: *mut PyObject) -> *const InterpreterState {
    unsafe {
        let states = INTERPRETER_STATES.get_or_init(|| Mutex::new(HashMap::new()));
        let mut guard = states.lock().unwrap();

        // Use entry API for efficient lookup/insert
        // Convert pointer to usize for HashMap key (safe for comparison only)
        let module_key = module as usize;
        let state_ptr = guard
            .entry(module_key)
            .or_insert_with(|| Box::new(InterpreterState::new()))
            .as_ref() as *const InterpreterState;

        // Leak the pointer - the state lives as long as the interpreter
        state_ptr
    }
}

thread_local! {
    // Cache interpreter ID and state pointer for fast access
    // Using interpreter ID is much cheaper than PyImport_ImportModule
    static CACHED_INTERP_ID: std::cell::Cell<i64> = const { std::cell::Cell::new(-1) };
    static CACHED_STATE: std::cell::Cell<*const InterpreterState> =
        const { std::cell::Cell::new(null_mut()) };
}

/// Get the current interpreter's state.
///
/// Uses thread-local caching with interpreter ID for fast detection.
/// PyInterpreterState_GetID is much cheaper than PyImport_ImportModule.
#[inline(always)]
pub(crate) unsafe fn get_current_state() -> *const InterpreterState {
    unsafe {
        // Get current interpreter ID - this is very fast
        let interp = crate::ffi::PyInterpreterState_Get();
        let interp_id = crate::ffi::PyInterpreterState_GetID(interp);

        // Check if we're in the same interpreter as cached
        let cached_id = CACHED_INTERP_ID.with(|cell| cell.get());
        if cached_id == interp_id {
            // Same interpreter - use cached state
            return CACHED_STATE.with(|cell| cell.get());
        }

        // Different interpreter or first call - look up state via module import
        let module = PyImport_ImportModule(c"hyperjson".as_ptr());
        if module.is_null() {
            core::hint::unreachable_unchecked();
        }
        let state = get_or_init_state(module);

        // Update cache
        CACHED_INTERP_ID.with(|cell| cell.set(interp_id));
        CACHED_STATE.with(|cell| cell.set(state));

        // Decref the import reference since sys.modules holds the real reference
        Py_DECREF(module);

        state
    }
}
