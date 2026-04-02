def _get_sqlite_columns(conn, table_name):
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return {r[1] for r in rows}


def _add_column(conn, table_name, col_name, col_type):
    conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")


def auto_migrate_sqlite(engine):
    if engine.dialect.name != 'sqlite':
        return

    table_columns = {
        'hosts': {
            'hostname': 'TEXT',
            'os_version': 'TEXT',
            'business_system_id': 'INTEGER',
            'owner': 'TEXT',
            'env': 'TEXT',
            'idc': 'TEXT',
            'remark': 'TEXT'
        },
        'databases': {
            'business_system_id': 'INTEGER',
            'owner': 'TEXT',
            'env': 'TEXT',
            'version': 'TEXT',
            'remark': 'TEXT'
        },
        'middlewares': {
            'business_system_id': 'INTEGER',
            'owner': 'TEXT',
            'env': 'TEXT',
            'remark': 'TEXT'
        }
    }

    with engine.begin() as conn:
        for table, cols in table_columns.items():
            existing = _get_sqlite_columns(conn, table)
            for col_name, col_type in cols.items():
                if col_name in existing:
                    continue
                _add_column(conn, table, col_name, col_type)
