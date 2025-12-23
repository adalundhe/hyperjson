// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2024-2025)

use crate::interpreter_state::InterpreterState;
use crate::opt::Opt;

const RECURSION_SHIFT: usize = 24;
const RECURSION_MASK: u32 = 255 << RECURSION_SHIFT;

const DEFAULT_SHIFT: usize = 16;
const DEFAULT_MASK: u32 = 255 << DEFAULT_SHIFT;

#[derive(Copy, Clone)]
pub(crate) struct SerializerState {
    // recursion: u8,
    // default_calls: u8,
    // opts: u16,
    state: u32,
    // Cached interpreter state pointer for fast access during serialization
    // Valid for the lifetime of the serialization call (GIL is held)
    interpreter_state: *const InterpreterState,
}

impl SerializerState {
    #[inline(always)]
    pub fn new(opts: Opt) -> Self {
        debug_assert!(opts < u32::from(u16::MAX));
        // Get interpreter state pointer once at the start of serialization
        // This avoids repeated thread-local lookups during serialization
        let interpreter_state = unsafe { crate::interpreter_state::get_current_state() };
        debug_assert!(!interpreter_state.is_null());
        Self {
            state: opts,
            interpreter_state,
        }
    }

    #[inline(always)]
    pub fn opts(self) -> u32 {
        self.state
    }

    #[inline(always)]
    pub fn recursion_limit(self) -> bool {
        self.state & RECURSION_MASK == RECURSION_MASK
    }

    #[inline(always)]
    pub fn default_calls_limit(self) -> bool {
        self.state & DEFAULT_MASK == DEFAULT_MASK
    }

    #[inline(always)]
    pub fn copy_for_recursive_call(self) -> Self {
        let opt = self.state & !RECURSION_MASK;
        let recursion = (((self.state & RECURSION_MASK) >> RECURSION_SHIFT) + 1) << RECURSION_SHIFT;
        Self {
            state: opt | recursion,
            interpreter_state: self.interpreter_state, // Preserve cached state pointer
        }
    }

    #[inline(always)]
    pub fn copy_for_default_call(self) -> Self {
        let opt = self.state & !DEFAULT_MASK;
        let default_calls = (((self.state & DEFAULT_MASK) >> DEFAULT_SHIFT) + 1) << DEFAULT_SHIFT;
        Self {
            state: opt | default_calls,
            interpreter_state: self.interpreter_state, // Preserve cached state pointer
        }
    }

    /// Get the cached interpreter state pointer
    /// This pointer is valid for the lifetime of serialization (GIL is held)
    #[inline(always)]
    pub(crate) fn interpreter_state(&self) -> *const InterpreterState {
        self.interpreter_state
    }
}
