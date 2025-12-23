// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2018-2025), Aviram Hassan (2020-2021), Nazar Kostetskyi (2022), Ben Sully (2021)

use core::ffi::CStr;
use core::ptr::{NonNull, null_mut};
use once_cell::race::OnceBox;

use crate::ffi::{
    Py_XDECREF, PyErr_Clear, PyImport_ImportModule, PyMapping_GetItemString, PyObject,
    PyObject_GenericGetDict, PyTypeObject,
};

// Accessor macros that use interpreter state instead of static variables
// These provide a drop-in replacement for the old static variables

#[macro_export]
macro_rules! get_state {
    () => {
        // Inline the state access for better optimization
        unsafe {
            let state_ptr = crate::interpreter_state::get_current_state();
            debug_assert!(!state_ptr.is_null());
            &*state_ptr
        }
    };
}

// Accessor functions for commonly used values
#[inline(always)]
pub(crate) fn get_default() -> *mut PyObject {
    unsafe { get_state!().default }
}

#[inline(always)]
pub(crate) fn get_option() -> *mut PyObject {
    unsafe { get_state!().option }
}

#[inline(always)]
pub(crate) fn get_none() -> *mut PyObject {
    unsafe { get_state!().none }
}

#[inline(always)]
pub(crate) fn get_true() -> *mut PyObject {
    unsafe { get_state!().true_ }
}

#[inline(always)]
pub(crate) fn get_false() -> *mut PyObject {
    unsafe { get_state!().false_ }
}

#[inline(always)]
pub(crate) fn get_empty_unicode() -> *mut PyObject {
    unsafe { get_state!().empty_unicode }
}

#[inline(always)]
pub(crate) fn get_int_type() -> *mut PyTypeObject {
    unsafe { get_state!().int_type }
}

#[inline(always)]
pub(crate) fn get_none_type() -> *mut PyTypeObject {
    unsafe { get_state!().none_type }
}

#[inline(always)]
pub(crate) fn get_fragment_type() -> *mut PyTypeObject {
    unsafe { get_state!().fragment_type }
}

#[inline(always)]
pub(crate) fn get_json_encode_error() -> *mut PyObject {
    unsafe { get_state!().json_encode_error }
}

#[inline(always)]
pub(crate) fn get_json_decode_error() -> *mut PyObject {
    unsafe { get_state!().json_decode_error }
}

// Additional accessors for string constants
#[inline(always)]
pub(crate) fn get_value_str() -> *mut PyObject {
    unsafe { get_state!().value_str }
}

#[inline(always)]
pub(crate) fn get_int_attr_str() -> *mut PyObject {
    unsafe { get_state!().int_attr_str }
}

// Type accessors
#[inline(always)]
pub(crate) fn get_bytes_type() -> *mut PyTypeObject {
    unsafe { get_state!().bytes_type }
}

#[inline(always)]
pub(crate) fn get_str_type() -> *mut PyTypeObject {
    unsafe { get_state!().str_type }
}

#[inline(always)]
pub(crate) fn get_bool_type() -> *mut PyTypeObject {
    unsafe { get_state!().bool_type }
}

#[inline(always)]
pub(crate) fn get_list_type() -> *mut PyTypeObject {
    unsafe { get_state!().list_type }
}

#[inline(always)]
pub(crate) fn get_dict_type() -> *mut PyTypeObject {
    unsafe { get_state!().dict_type }
}

#[inline(always)]
pub(crate) fn get_tuple_type() -> *mut PyTypeObject {
    unsafe { get_state!().tuple_type }
}

#[inline(always)]
pub(crate) fn get_datetime_type() -> *mut PyTypeObject {
    unsafe { get_state!().datetime_type }
}

#[inline(always)]
pub(crate) fn get_date_type() -> *mut PyTypeObject {
    unsafe { get_state!().date_type }
}

#[inline(always)]
pub(crate) fn get_time_type() -> *mut PyTypeObject {
    unsafe { get_state!().time_type }
}

#[inline(always)]
pub(crate) fn get_uuid_type() -> *mut PyTypeObject {
    unsafe { get_state!().uuid_type }
}

#[inline(always)]
pub(crate) fn get_enum_type() -> *mut PyTypeObject {
    unsafe { get_state!().enum_type }
}

#[inline(always)]
pub(crate) fn get_field_type() -> *mut PyTypeObject {
    unsafe { get_state!().field_type }
}

#[inline(always)]
pub(crate) fn get_zoneinfo_type() -> *mut PyTypeObject {
    unsafe { get_state!().zoneinfo_type }
}

#[inline(always)]
pub(crate) fn get_float_type() -> *mut PyTypeObject {
    unsafe { get_state!().float_type }
}

#[inline(always)]
pub(crate) fn get_bytearray_type() -> *mut PyTypeObject {
    unsafe { get_state!().bytearray_type }
}

#[inline(always)]
pub(crate) fn get_memoryview_type() -> *mut PyTypeObject {
    unsafe { get_state!().memoryview_type }
}

// String constant accessors
#[inline(always)]
pub(crate) fn get_utcoffset_method_str() -> *mut PyObject {
    unsafe { get_state!().utcoffset_method_str }
}

#[inline(always)]
pub(crate) fn get_normalize_method_str() -> *mut PyObject {
    unsafe { get_state!().normalize_method_str }
}

#[inline(always)]
pub(crate) fn get_convert_method_str() -> *mut PyObject {
    unsafe { get_state!().convert_method_str }
}

#[inline(always)]
pub(crate) fn get_dst_str() -> *mut PyObject {
    unsafe { get_state!().dst_str }
}

#[inline(always)]
pub(crate) fn get_dict_str() -> *mut PyObject {
    unsafe { get_state!().dict_str }
}

#[inline(always)]
pub(crate) fn get_dataclass_fields_str() -> *mut PyObject {
    unsafe { get_state!().dataclass_fields_str }
}

#[inline(always)]
pub(crate) fn get_slots_str() -> *mut PyObject {
    unsafe { get_state!().slots_str }
}

#[inline(always)]
pub(crate) fn get_field_type_str() -> *mut PyObject {
    unsafe { get_state!().field_type_str }
}

#[inline(always)]
pub(crate) fn get_array_struct_str() -> *mut PyObject {
    unsafe { get_state!().array_struct_str }
}

#[inline(always)]
pub(crate) fn get_dtype_str() -> *mut PyObject {
    unsafe { get_state!().dtype_str }
}

#[inline(always)]
pub(crate) fn get_descr_str() -> *mut PyObject {
    unsafe { get_state!().descr_str }
}


pub(crate) struct NumpyTypes {
    pub array: *mut PyTypeObject,
    pub float64: *mut PyTypeObject,
    pub float32: *mut PyTypeObject,
    pub float16: *mut PyTypeObject,
    pub int64: *mut PyTypeObject,
    pub int32: *mut PyTypeObject,
    pub int16: *mut PyTypeObject,
    pub int8: *mut PyTypeObject,
    pub uint64: *mut PyTypeObject,
    pub uint32: *mut PyTypeObject,
    pub uint16: *mut PyTypeObject,
    pub uint8: *mut PyTypeObject,
    pub bool_: *mut PyTypeObject,
    pub datetime64: *mut PyTypeObject,
}

pub(crate) static mut NUMPY_TYPES: OnceBox<Option<NonNull<NumpyTypes>>> = OnceBox::new();

unsafe fn look_up_numpy_type(
    numpy_module_dict: *mut PyObject,
    np_type: &CStr,
) -> *mut PyTypeObject {
    unsafe {
        let ptr = PyMapping_GetItemString(numpy_module_dict, np_type.as_ptr());
        Py_XDECREF(ptr);
        ptr.cast::<PyTypeObject>()
    }
}

#[cold]
#[cfg_attr(feature = "optimize", optimize(size))]
pub(crate) fn load_numpy_types() -> Box<Option<NonNull<NumpyTypes>>> {
    unsafe {
        let numpy = PyImport_ImportModule(c"numpy".as_ptr());
        if numpy.is_null() {
            PyErr_Clear();
            return Box::new(None);
        }
        let numpy_module_dict = PyObject_GenericGetDict(numpy, null_mut());
        let types = Box::new(NumpyTypes {
            array: look_up_numpy_type(numpy_module_dict, c"ndarray"),
            float16: look_up_numpy_type(numpy_module_dict, c"half"),
            float32: look_up_numpy_type(numpy_module_dict, c"float32"),
            float64: look_up_numpy_type(numpy_module_dict, c"float64"),
            int8: look_up_numpy_type(numpy_module_dict, c"int8"),
            int16: look_up_numpy_type(numpy_module_dict, c"int16"),
            int32: look_up_numpy_type(numpy_module_dict, c"int32"),
            int64: look_up_numpy_type(numpy_module_dict, c"int64"),
            uint16: look_up_numpy_type(numpy_module_dict, c"uint16"),
            uint32: look_up_numpy_type(numpy_module_dict, c"uint32"),
            uint64: look_up_numpy_type(numpy_module_dict, c"uint64"),
            uint8: look_up_numpy_type(numpy_module_dict, c"uint8"),
            bool_: look_up_numpy_type(numpy_module_dict, c"bool_"),
            datetime64: look_up_numpy_type(numpy_module_dict, c"datetime64"),
        });
        Py_XDECREF(numpy_module_dict);
        Py_XDECREF(numpy);
        Box::new(Some(nonnull!(Box::<NumpyTypes>::into_raw(types))))
    }
}
