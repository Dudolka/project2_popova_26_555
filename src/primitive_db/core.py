"""Database schema and CRUD business logic."""

from primitive_db.constants import ID_COLUMN, VALID_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data

_cache_result = create_cacher()
_cache_generation = 0


def invalidate_cache():
    """Advance the cache version after data mutation."""
    global _cache_generation
    _cache_generation += 1


def require_table(metadata, table_name):
    """Return a table schema or raise an informative error."""
    if table_name not in metadata:
        raise KeyError(f'Таблица "{table_name}" не существует.')
    return metadata[table_name]


def schema_items(schema):
    """Normalize schema stored as column:type tokens or a mapping."""
    if isinstance(schema, dict):
        return list(schema.items())
    return [tuple(item.split(":", 1)) for item in schema]


def validate_name(name):
    """Validate an identifier used as a table or column name."""
    if not name.isidentifier() or name.startswith("_"):
        raise ValueError(f"Некорректное значение: {name}. Попробуйте снова.")


def create_table(metadata, table_name, columns):
    """Add a table schema, including its automatically managed ID column."""
    validate_name(table_name)
    if table_name in metadata:
        raise ValueError(f'Таблица "{table_name}" уже существует.')
    if not columns:
        raise ValueError("Необходимо указать хотя бы один столбец.")
    schema = ["ID:int"]
    names = {ID_COLUMN}
    for column in columns:
        if column.count(":") != 1:
            raise ValueError(f"Некорректное значение: {column}. Попробуйте снова.")
        name, data_type = column.split(":")
        validate_name(name)
        if name in names or data_type not in VALID_TYPES:
            raise ValueError(f"Некорректное значение: {column}. Попробуйте снова.")
        names.add(name)
        schema.append(column)
    metadata[table_name] = schema
    print(f'Таблица "{table_name}" успешно создана со столбцами: {", ".join(schema)}')
    invalidate_cache()
    return metadata


@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Remove a table schema after confirmation."""
    require_table(metadata, table_name)
    del metadata[table_name]
    invalidate_cache()
    print(f'Таблица "{table_name}" успешно удалена.')
    return metadata


def check_value(value, data_type):
    """Reject values that do not match their declared column type."""
    if data_type == "int" and type(value) is int:
        return
    if data_type == "str" and type(value) is str:
        return
    if data_type == "bool" and type(value) is bool:
        return
    raise ValueError(f"Некорректное значение: {value}. Ожидается {data_type}.")


def check_clause(schema, clause, allow_id=True):
    """Validate a condition or assignment against a table schema."""
    fields = dict(schema_items(schema))
    for column, value in clause.items():
        if column not in fields:
            raise KeyError(f'Столбец "{column}" не существует.')
        if column == ID_COLUMN and not allow_id:
            raise ValueError("Изменять ID запрещено.")
        check_value(value, fields[column])


@log_time
def insert(metadata, table_name, values):
    """Validate and append a row, returning the updated row list."""
    schema = schema_items(require_table(metadata, table_name))
    if len(values) != len(schema) - 1:
        raise ValueError("Количество значений не соответствует структуре таблицы.")
    rows = load_table_data(table_name)
    row = {ID_COLUMN: max((item[ID_COLUMN] for item in rows), default=0) + 1}
    for (column, data_type), value in zip(schema[1:], values, strict=True):
        check_value(value, data_type)
        row[column] = value
    rows.append(row)
    invalidate_cache()
    print(f'Запись с ID={row[ID_COLUMN]} успешно добавлена в таблицу "{table_name}".')
    return rows


@log_time
def select(table_data, where_clause=None):
    """Return all matching rows, using a closure-based versioned cache."""
    key = (
        _cache_generation,
        repr(table_data),
        tuple(sorted(where_clause.items())) if where_clause else None,
    )
    return _cache_result(
        key,
        lambda: [
            row.copy()
            for row in table_data
            if not where_clause
            or all(row.get(column) == value for column, value in where_clause.items())
        ],
    )


def update(table_data, set_clause, where_clause):
    """Update rows matching a condition and return the changed data."""
    for row in table_data:
        if all(row.get(key) == value for key, value in where_clause.items()):
            row.update(set_clause)
            print(f"Запись с ID={row[ID_COLUMN]} успешно обновлена.")
    invalidate_cache()
    return table_data


@confirm_action("удаление записи")
def delete(table_data, where_clause):
    """Delete matching rows after user confirmation."""
    removed = [
        row
        for row in table_data
        if all(row.get(key) == value for key, value in where_clause.items())
    ]
    table_data[:] = [row for row in table_data if row not in removed]
    for row in removed:
        print(f"Запись с ID={row[ID_COLUMN]} успешно удалена.")
    invalidate_cache()
    return table_data


safe_create_table = handle_db_errors(create_table)
safe_drop_table = handle_db_errors(drop_table)
safe_insert = handle_db_errors(insert)
safe_select = handle_db_errors(select)
safe_update = handle_db_errors(update)
safe_delete = handle_db_errors(delete)
