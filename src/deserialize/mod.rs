// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2020-2025), Eric Jolibois (2021)

mod backend;
#[cfg(not(Py_GIL_DISABLED))]
pub(crate) mod cache;
mod deserializer;
mod error;
mod pyobject;
mod utf8;

pub(crate) use deserializer::deserialize;
pub(crate) use error::DeserializeError;
