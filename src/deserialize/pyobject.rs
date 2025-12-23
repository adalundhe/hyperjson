// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2022-2025)

#[cfg(not(Py_GIL_DISABLED))]
use crate::deserialize::cache::CachedKey;
use crate::str::PyStr;
// NONE, TRUE, FALSE now accessed via typeref accessor functions
use core::ptr::NonNull;

#[cfg(not(Py_GIL_DISABLED))]
#[inline(always)]
pub(crate) fn get_unicode_key(
    key_str: &str,
    interpreter_state: *const crate::interpreter_state::InterpreterState,
) -> PyStr {
    if key_str.len() > 64 {
        cold_path!();
        PyStr::from_str_with_hash(key_str)
    } else {
        assume!(key_str.len() <= 64);
        let hash = xxhash_rust::xxh3::xxh3_64(key_str.as_bytes());
        unsafe {
            debug_assert!(!interpreter_state.is_null());
            let state = &*interpreter_state;
            let key_map = &mut *state.key_map.get();
            let entry = key_map.entry(&hash).or_insert_with(
                || hash,
                || CachedKey::new(PyStr::from_str_with_hash(key_str)),
            );
            entry.get()
        }
    }
}

#[cfg(Py_GIL_DISABLED)]
#[inline(always)]
pub(crate) fn get_unicode_key(key_str: &str) -> PyStr {
    PyStr::from_str_with_hash(key_str)
}

#[inline(always)]
pub(crate) fn parse_i64(val: i64) -> NonNull<crate::ffi::PyObject> {
    nonnull!(ffi!(PyLong_FromLongLong(val)))
}

#[inline(always)]
pub(crate) fn parse_u64(val: u64) -> NonNull<crate::ffi::PyObject> {
    nonnull!(ffi!(PyLong_FromUnsignedLongLong(val)))
}

#[inline(always)]
pub(crate) fn parse_f64(val: f64) -> NonNull<crate::ffi::PyObject> {
    nonnull!(ffi!(PyFloat_FromDouble(val)))
}

// Optimized parse functions using direct CPython globals
// No state lookup needed - these are CPython singletons
#[inline(always)]
pub(crate) fn parse_true_with_state(
    _state: *const crate::interpreter_state::InterpreterState,
) -> NonNull<crate::ffi::PyObject> {
    unsafe { nonnull!(use_immortal!(crate::typeref::true_ptr())) }
}

#[inline(always)]
pub(crate) fn parse_false_with_state(
    _state: *const crate::interpreter_state::InterpreterState,
) -> NonNull<crate::ffi::PyObject> {
    unsafe { nonnull!(use_immortal!(crate::typeref::false_ptr())) }
}

#[inline(always)]
pub(crate) fn parse_none_with_state(
    _state: *const crate::interpreter_state::InterpreterState,
) -> NonNull<crate::ffi::PyObject> {
    unsafe { nonnull!(use_immortal!(crate::typeref::none_ptr())) }
}
