"""Interactive command loop for the primitive database."""

import re
import shlex

from prettytable import PrettyTable

from primitive_db import core
from primitive_db.constants import META_FILE, PROMPT
from primitive_db.parser import parse_condition, parse_values, split_command
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
    table_path,
)

HELP_TEXT = """
***Процесс работы с таблицей***
Функции:
<command> create_table <имя_таблицы> <столбец1:тип> ... - создать таблицу
<command> list_tables - показать список всех таблиц
<command> drop_table <имя_таблицы> - удалить таблицу

***Операции с данными***
<command> insert into <таблица> values (<значения>) - добавить запись
<command> select from <таблица> [where <поле> = <значение>] - выборка
<command> update <таблица> set <поле> = <значение> where ... - изменить
<command> delete from <таблица> where <поле> = <значение> - удалить
<command> info <таблица> - информация о таблице
<command> help - справочная информация
<command> exit - выход из программы
"""


def print_help():
    """Show available commands and their syntax."""
    print(HELP_TEXT)


def welcome():
    """Display a greeting when the console starts."""
    print("***База данных***")
    print_help()


def _where_clause(expression, schema):
    """Parse and validate one WHERE clause."""
    clause = parse_condition(expression)
    core.check_clause(schema, clause)
    return clause


def _display_rows(rows, schema):
    """Render matching rows with PrettyTable."""
    names = [name for name, _ in core.schema_items(schema)]
    table = PrettyTable()
    table.field_names = names
    for row in rows:
        table.add_row([row[name] for name in names])
    print(table)


def _handle_schema(command, tokens, metadata):
    """Execute table schema operations and persist successful changes."""
    if command == "list_tables":
        if len(tokens) != 1:
            raise ValueError("Команда list_tables не принимает аргументы.")
        for table_name in metadata:
            print(f"- {table_name}")
        if not metadata:
            print("Таблиц нет.")
        return
    if command == "create_table":
        if len(tokens) < 3:
            raise ValueError("Укажите таблицу и хотя бы один столбец.")
        updated = core.safe_create_table(metadata, tokens[1], tokens[2:])
        if updated is not None:
            save_metadata(META_FILE, updated)
            save_table_data(tokens[1], [])
        return
    if len(tokens) != 2:
        raise ValueError("Укажите имя таблицы.")
    core.require_table(metadata, tokens[1])
    updated = core.safe_drop_table(metadata, tokens[1])
    if updated is not None:
        save_metadata(META_FILE, updated)
        table_path(tokens[1]).unlink(missing_ok=True)


def _handle_crud(user_input, metadata):
    """Execute CRUD commands parsed from the raw input."""
    command = user_input.split(maxsplit=1)[0].lower()
    if command == "insert":
        match = re.fullmatch(
            r"insert\s+into\s+(\w+)\s+values\s*(\(.*\))\s*",
            user_input,
            re.IGNORECASE,
        )
        if match is None:
            raise ValueError("Некорректный синтаксис insert.")
        table_name, expression = match.groups()
        values = parse_values(expression)
        rows = core.safe_insert(metadata, table_name, values)
        if rows is not None:
            save_table_data(table_name, rows)
        return
    if command == "select":
        match = re.fullmatch(
            r"select\s+from\s+(\w+)(?:\s+where\s+(.+))?\s*",
            user_input,
            re.IGNORECASE,
        )
        if match is None:
            raise ValueError("Некорректный синтаксис select.")
        table_name, expression = match.groups()
        schema = core.require_table(metadata, table_name)
        clause = _where_clause(expression, schema) if expression else None
        rows = core.safe_select(load_table_data(table_name), clause)
        if rows is not None:
            _display_rows(rows, schema)
        return
    if command == "update":
        match = re.fullmatch(
            r"update\s+(\w+)\s+set\s+(.+?)\s+where\s+(.+)\s*",
            user_input,
            re.IGNORECASE,
        )
        if match is None:
            raise ValueError("Некорректный синтаксис update.")
        table_name, assignment, condition = match.groups()
        schema = core.require_table(metadata, table_name)
        set_clause = parse_condition(assignment)
        core.check_clause(schema, set_clause, allow_id=False)
        where_clause = _where_clause(condition, schema)
        rows = core.safe_update(load_table_data(table_name), set_clause, where_clause)
        if rows is not None:
            save_table_data(table_name, rows)
        return
    if command == "delete":
        match = re.fullmatch(
            r"delete\s+from\s+(\w+)\s+where\s+(.+)\s*",
            user_input,
            re.IGNORECASE,
        )
        if match is None:
            raise ValueError("Некорректный синтаксис delete.")
        table_name, condition = match.groups()
        schema = core.require_table(metadata, table_name)
        where_clause = _where_clause(condition, schema)
        rows = core.safe_delete(load_table_data(table_name), where_clause)
        if rows is not None:
            save_table_data(table_name, rows)
        return
    tokens = split_command(user_input)
    if len(tokens) != 2:
        raise ValueError("Укажите имя таблицы.")
    table_name = tokens[1]
    schema = core.require_table(metadata, table_name)
    print(f"Таблица: {table_name}")
    print(
        "Столбцы: "
        + ", ".join(f"{name}:{kind}" for name, kind in core.schema_items(schema))
    )
    print(f"Количество записей: {len(load_table_data(table_name))}")


def run():
    """Read commands until exit, persisting every successful mutation."""
    welcome()
    while True:
        try:
            user_input = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print("Выход из программы.")
            break
        if not user_input:
            continue
        try:
            tokens = shlex.split(user_input)
            if not tokens:
                continue
            command = tokens[0].lower()
            metadata = load_metadata(META_FILE)
            if command == "exit":
                print("Выход из программы.")
                break
            if command == "help":
                print_help()
            elif command in ("create_table", "drop_table", "list_tables"):
                _handle_schema(command, tokens, metadata)
            elif command in ("insert", "select", "update", "delete", "info"):
                _handle_crud(user_input, metadata)
            else:
                print(f"Функции {command} нет. Попробуйте снова.")
        except (ValueError, KeyError, FileNotFoundError) as error:
            print(f"Ошибка: {error}")
