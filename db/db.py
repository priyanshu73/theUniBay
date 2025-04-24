import sqlite3
import click
import os
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    """Connects to the application's configured database.
    The connection is unique for each request and will be reused if called again.
    """
    if 'db' not in g:
        try:
            db_path = current_app.config['DATABASE']
            g.db = sqlite3.connect(
                db_path,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row 
            print(f"Database connection established to: {db_path}")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise 
    return g.db

def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        print("Database connection closed.")

def init_db():
    """Clear existing data and create new tables."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    try:
        with current_app.open_resource(schema_path, 'rt') as f: 
            db.executescript(f.read())
        print("Initialized the database schema.")
    except FileNotFoundError:
        print(f"Schema file not found at expected location based on app context: {schema_path}")
    except sqlite3.Error as e:
        print(f"Error executing schema: {e}")


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Flask CLI command to initialize the database."""
    import os 
    print("Attempting to initialize database...")
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)