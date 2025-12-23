// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2019-2025)

use crate::str::PyStr;

/// FNV-1a 64-bit hash - simple, fast, good distribution for short strings
/// This is significantly faster than xxhash for short strings (< 64 bytes)
/// because it has no setup cost and is branch-free
#[inline(always)]
pub(crate) fn fnv1a_hash(data: &[u8]) -> u64 {
    const FNV_OFFSET: u64 = 0xcbf29ce484222325;
    const FNV_PRIME: u64 = 0x100000001b3;

    let mut hash = FNV_OFFSET;
    for &byte in data {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    hash
}

/// Simple direct-mapped cache entry
/// Stores a PyStr with its hash for collision detection
pub(crate) struct CacheEntry {
    /// The cached Python string (null if slot is empty)
    ptr: *mut crate::ffi::PyObject,
    /// The FNV hash of the string (for collision detection)
    hash: u64,
    /// Length of the original string (for quick mismatch detection)
    len: u8,
}

impl CacheEntry {
    #[inline(always)]
    const fn empty() -> Self {
        CacheEntry {
            ptr: core::ptr::null_mut(),
            hash: 0,
            len: 0,
        }
    }
}

/// Cache size - power of 2 for fast modulo (bitwise AND)
/// 2048 entries = 2048 * 24 bytes = ~48KB - fits in L2 cache
const CACHE_SIZE: usize = 2048;
const CACHE_MASK: usize = CACHE_SIZE - 1;

/// Simple direct-mapped key cache
/// - O(1) lookup with single array access
/// - Uses FNV-1a hash for index and collision detection
/// - No dynamic allocation after initialization
pub(crate) struct KeyCache {
    entries: [CacheEntry; CACHE_SIZE],
}

impl KeyCache {
    pub fn new() -> Self {
        // Initialize with empty entries
        // Using array initialization with const fn
        KeyCache {
            entries: [const { CacheEntry::empty() }; CACHE_SIZE],
        }
    }

    /// Get or insert a cached key
    /// Returns the PyStr (with incremented refcount)
    #[inline(always)]
    pub unsafe fn get_or_insert(&mut self, key_str: &str) -> PyStr {
        unsafe {
            let bytes = key_str.as_bytes();
            let hash = fnv1a_hash(bytes);
            let index = (hash as usize) & CACHE_MASK;
            let len = bytes.len() as u8;

            let entry = &mut self.entries[index];

            // Fast path: cache hit (hash and length match)
            if !entry.ptr.is_null() && entry.hash == hash && entry.len == len {
                // Hit - increment refcount and return
                ffi!(Py_INCREF(entry.ptr));
                return PyStr::from_ptr_unchecked(entry.ptr);
            }

            // Cache miss - create new string and cache it
            let new_str = PyStr::from_str_with_hash(key_str);
            let new_ptr = new_str.as_ptr();

            // Evict old entry if present
            if !entry.ptr.is_null() {
                ffi!(Py_DECREF(entry.ptr));
            }

            // Store new entry (keep one reference for cache)
            ffi!(Py_INCREF(new_ptr));
            entry.ptr = new_ptr;
            entry.hash = hash;
            entry.len = len;

            new_str
        }
    }
}

impl Default for KeyCache {
    fn default() -> Self {
        Self::new()
    }
}

impl Drop for KeyCache {
    fn drop(&mut self) {
        for entry in &mut self.entries {
            if !entry.ptr.is_null() {
                ffi!(Py_DECREF(entry.ptr));
                entry.ptr = core::ptr::null_mut();
            }
        }
    }
}
