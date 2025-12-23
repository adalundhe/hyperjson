// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2022-2025)

use crate::str::PyStr;
use core::ptr::NonNull;

/// Get a cached unicode key for dictionary keys.
/// Uses a simple direct-mapped cache with FNV-1a hashing for maximum speed.
#[cfg(not(Py_GIL_DISABLED))]
#[inline(always)]
pub(crate) fn get_unicode_key(
    key_str: &str,
    interpreter_state: *const crate::interpreter_state::InterpreterState,
) -> PyStr {
    // Long keys (>64 bytes) - unlikely to repeat, skip cache
    // Also keys > 255 bytes can't fit in u8 len field
    if key_str.len() > 64 {
        cold_path!();
        return PyStr::from_str_with_hash(key_str);
    }

    // Fast path: direct cache lookup with FNV hash
    assume!(key_str.len() <= 64);
    unsafe {
        let cache = &mut *(*interpreter_state).key_map.get();
        cache.get_or_insert(key_str)
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
// Zero overhead - no state parameter, no lookup

#[inline(always)]
pub(crate) fn parse_true() -> NonNull<crate::ffi::PyObject> {
    unsafe { nonnull!(use_immortal!(crate::typeref::true_ptr())) }
}

#[inline(always)]
pub(crate) fn parse_false() -> NonNull<crate::ffi::PyObject> {
    unsafe { nonnull!(use_immortal!(crate::typeref::false_ptr())) }
}

#[inline(always)]
pub(crate) fn parse_none() -> NonNull<crate::ffi::PyObject> {
    unsafe { nonnull!(use_immortal!(crate::typeref::none_ptr())) }
}
