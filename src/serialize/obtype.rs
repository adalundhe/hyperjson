// SPDX-License-Identifier: (Apache-2.0 OR MIT)
// Copyright ijl (2020-2025), Aviram Hassan (2020)

use crate::opt::{
    Opt, PASSTHROUGH_DATACLASS, PASSTHROUGH_DATETIME, PASSTHROUGH_SUBCLASS, SERIALIZE_NUMPY,
};
use crate::serialize::per_type::{is_numpy_array, is_numpy_scalar};
// Type constants now accessed via typeref accessor functions

#[repr(u32)]
pub(crate) enum ObType {
    Str,
    Int,
    Bool,
    None,
    Float,
    List,
    Dict,
    Datetime,
    Date,
    Time,
    Tuple,
    Uuid,
    Dataclass,
    NumpyScalar,
    NumpyArray,
    Enum,
    StrSubclass,
    Fragment,
    Unknown,
}

pub(crate) fn pyobject_to_obtype(
    obj: *mut crate::ffi::PyObject,
    opts: Opt,
    interpreter_state: *const crate::interpreter_state::InterpreterState,
) -> ObType {
    let ob_type = ob_type!(obj);
    // Use direct CPython global accessors for built-in types (zero indirection)
    if is_class_by_type!(ob_type, crate::typeref::str_type_ptr()) {
        ObType::Str
    } else if is_class_by_type!(ob_type, crate::typeref::int_type_ptr()) {
        ObType::Int
    } else if is_class_by_type!(ob_type, crate::typeref::bool_type_ptr()) {
        ObType::Bool
    } else if is_class_by_type!(ob_type, crate::typeref::none_type_ptr()) {
        ObType::None
    } else if is_class_by_type!(ob_type, crate::typeref::float_type_ptr()) {
        ObType::Float
    } else if is_class_by_type!(ob_type, crate::typeref::list_type_ptr()) {
        ObType::List
    } else if is_class_by_type!(ob_type, crate::typeref::dict_type_ptr()) {
        ObType::Dict
    } else if is_class_by_type!(
        ob_type,
        crate::typeref::get_datetime_type_from_state(interpreter_state)
    ) && opt_disabled!(opts, PASSTHROUGH_DATETIME)
    {
        ObType::Datetime
    } else {
        pyobject_to_obtype_unlikely(ob_type, opts, interpreter_state)
    }
}

#[cfg_attr(feature = "optimize", optimize(size))]
#[inline(never)]
pub(crate) fn pyobject_to_obtype_unlikely(
    ob_type: *mut crate::ffi::PyTypeObject,
    opts: Opt,
    interpreter_state: *const crate::interpreter_state::InterpreterState,
) -> ObType {
    if is_class_by_type!(
        ob_type,
        crate::typeref::get_uuid_type_from_state(interpreter_state)
    ) {
        return ObType::Uuid;
    } else if is_class_by_type!(ob_type, crate::typeref::tuple_type_ptr()) {
        // Use direct CPython global for tuple type
        return ObType::Tuple;
    } else if is_class_by_type!(
        ob_type,
        crate::typeref::get_fragment_type_from_state(interpreter_state)
    ) {
        return ObType::Fragment;
    }

    if opt_disabled!(opts, PASSTHROUGH_DATETIME) {
        if is_class_by_type!(
            ob_type,
            crate::typeref::get_date_type_from_state(interpreter_state)
        ) {
            return ObType::Date;
        } else if is_class_by_type!(
            ob_type,
            crate::typeref::get_time_type_from_state(interpreter_state)
        ) {
            return ObType::Time;
        }
    }

    let tp_flags = tp_flags!(ob_type);

    if opt_disabled!(opts, PASSTHROUGH_SUBCLASS) {
        if is_subclass_by_flag!(tp_flags, Py_TPFLAGS_UNICODE_SUBCLASS) {
            return ObType::StrSubclass;
        } else if is_subclass_by_flag!(tp_flags, Py_TPFLAGS_LONG_SUBCLASS) {
            return ObType::Int;
        } else if is_subclass_by_flag!(tp_flags, Py_TPFLAGS_LIST_SUBCLASS) {
            return ObType::List;
        } else if is_subclass_by_flag!(tp_flags, Py_TPFLAGS_DICT_SUBCLASS) {
            return ObType::Dict;
        }
    }

    if is_subclass_by_type!(
        ob_type,
        crate::typeref::get_enum_type_from_state(interpreter_state)
    ) {
        return ObType::Enum;
    }

    if opt_disabled!(opts, PASSTHROUGH_DATACLASS)
        && pydict_contains!(
            ob_type,
            crate::typeref::get_dataclass_fields_str_from_state(interpreter_state)
        )
    {
        return ObType::Dataclass;
    }

    if opt_enabled!(opts, SERIALIZE_NUMPY) {
        cold_path!();
        if is_numpy_scalar(ob_type) {
            return ObType::NumpyScalar;
        } else if is_numpy_array(ob_type) {
            return ObType::NumpyArray;
        }
    }

    ObType::Unknown
}
