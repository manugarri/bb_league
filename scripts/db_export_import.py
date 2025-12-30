#!/usr/bin/env python
"""Database export and import utilities."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from sqlalchemy import inspect


def get_all_tables():
    """Get all table names from the database."""
    inspector = inspect(db.engine)
    return inspector.get_table_names()


def serialize_value(value):
    """Serialize a value for JSON export."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value


def deserialize_value(value, column_type):
    """Deserialize a value from JSON import."""
    if value is None:
        return None
    
    type_name = str(column_type).upper()
    
    if 'DATETIME' in type_name or 'TIMESTAMP' in type_name:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
    
    return value


def export_database(output_file: str):
    """Export all database tables to a JSON file."""
    app = create_app()
    
    with app.app_context():
        tables = get_all_tables()
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "tables": {}
        }
        
        for table_name in tables:
            # Skip alembic version table
            if table_name == 'alembic_version':
                continue
            
            print(f"Exporting table: {table_name}")
            
            # Get table metadata
            table = db.metadata.tables.get(table_name)
            if table is None:
                print(f"  Warning: Table {table_name} not found in metadata, skipping...")
                continue
            
            # Get all rows
            result = db.session.execute(table.select())
            rows = result.fetchall()
            
            # Get column names
            columns = [col.name for col in table.columns]
            
            # Serialize rows
            table_data = []
            for row in rows:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    row_dict[col_name] = serialize_value(row[i])
                table_data.append(row_dict)
            
            export_data["tables"][table_name] = {
                "columns": columns,
                "rows": table_data,
                "count": len(table_data)
            }
            
            print(f"  Exported {len(table_data)} rows")
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nDatabase exported to: {output_path}")
        print(f"Total tables: {len(export_data['tables'])}")


def import_database(input_file: str, clear_existing: bool = True):
    """Import database from a JSON file."""
    app = create_app()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    print(f"Importing from: {input_path}")
    print(f"Export date: {import_data.get('exported_at', 'Unknown')}")
    
    with app.app_context():
        if clear_existing:
            print("\nClearing existing data...")
            # Get all tables in reverse order (to handle foreign keys)
            tables = get_all_tables()
            for table_name in reversed(tables):
                if table_name == 'alembic_version':
                    continue
                table = db.metadata.tables.get(table_name)
                if table is not None:
                    db.session.execute(table.delete())
            db.session.commit()
            print("Existing data cleared.")
        
        # Import tables in order (respecting foreign keys)
        # We'll try multiple passes to handle dependencies
        tables_to_import = list(import_data["tables"].keys())
        imported_tables = set()
        max_passes = 5
        
        for pass_num in range(max_passes):
            if not tables_to_import:
                break
            
            remaining = []
            for table_name in tables_to_import:
                table = db.metadata.tables.get(table_name)
                if table is None:
                    print(f"Warning: Table {table_name} not found in metadata, skipping...")
                    continue
                
                table_info = import_data["tables"][table_name]
                rows = table_info["rows"]
                
                if not rows:
                    imported_tables.add(table_name)
                    continue
                
                try:
                    print(f"Importing table: {table_name} ({len(rows)} rows)")
                    
                    # Get column types for deserialization
                    column_types = {col.name: col.type for col in table.columns}
                    
                    # Prepare rows for insert
                    insert_rows = []
                    for row in rows:
                        insert_row = {}
                        for col_name, value in row.items():
                            if col_name in column_types:
                                insert_row[col_name] = deserialize_value(
                                    value, column_types[col_name]
                                )
                        insert_rows.append(insert_row)
                    
                    # Insert in batches
                    batch_size = 100
                    for i in range(0, len(insert_rows), batch_size):
                        batch = insert_rows[i:i + batch_size]
                        db.session.execute(table.insert(), batch)
                    
                    db.session.commit()
                    imported_tables.add(table_name)
                    print(f"  Imported {len(rows)} rows")
                    
                except Exception as e:
                    db.session.rollback()
                    if pass_num < max_passes - 1:
                        remaining.append(table_name)
                    else:
                        print(f"  Error importing {table_name}: {e}")
            
            tables_to_import = remaining
        
        print(f"\nImport complete. Tables imported: {len(imported_tables)}")


def main():
    parser = argparse.ArgumentParser(description="Database export/import utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export database to JSON")
    export_parser.add_argument(
        "-o", "--output",
        default="backups/db_export.json",
        help="Output file path (default: backups/db_export.json)"
    )
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import database from JSON")
    import_parser.add_argument(
        "-i", "--input",
        default="backups/db_export.json",
        help="Input file path (default: backups/db_export.json)"
    )
    import_parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing data before import"
    )
    
    args = parser.parse_args()
    
    if args.command == "export":
        export_database(args.output)
    elif args.command == "import":
        import_database(args.input, clear_existing=not args.no_clear)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

