from app import create_app

app = create_app()

if __name__ == '__main__':
    # Note: 'flask run' command is preferred over app.run() for development
    # This block is mainly for other execution methods if needed
    app.run()