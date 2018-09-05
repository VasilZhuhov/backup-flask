import os
from wand.image import Image
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, send_from_directory
from werkzeug.utils import secure_filename


# create our little application :)
app = Flask(__name__)
UPLOAD_FOLDER = 'C:/Users/Vaseto/source/repos/Libary/uploads'
ALLOWED_EXTENSIONS = set(['pdf'])

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'libary.db'),
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='admin'
))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def load_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('data.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


@app.cli.command('load')
def load_command():
    """Creates the database tables."""
    load_db()
    print('Data loaded.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def check_user(username, password):
    db = get_db()
    data = db.execute('select * from users').fetchall()
    for i in data:
        if i[1] == username and i[2] == password:
            return True
    return False


def check_user_username(username):
    db = get_db()
    data = db.execute('select name from users').fetchall()
    for i in data:
        if i[0] == username:
            return True
    return False


@app.route('/my_books')
def show():
    db = get_db()
    username = session['username']
    query = 'select title from books where owner = ? '
    usernames = db.execute(query, [username]).fetchall()
    return render_template('database.html', data=usernames)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    query = 'insert into users(name, password) values (?, ?)'
    if request.method == 'POST':
        if not check_user_username(request.form['username']):
            username = request.form['username']
            password = request.form['password']
            db = get_db()
            db.execute(query, [username, password])
            db.commit()
            return redirect(url_for('login'))
        else:
            error = 'There is already user with this name'
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if check_user(request.form['username'], request.form['password']):
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('you are logged')
            return redirect(url_for('show', _external=True))
        else:
            error = 'There is no such user'
    return render_template('login.html', error=error)


@app.route('/book_libary')
def book_libary():
    db = get_db()
    curr = db.execute('select title from books')
    books = curr.fetchall()
    return render_template('database.html', books=books)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if not session.get('logged_in'):
        abort(401)

    if request.method == 'POST':
        db = get_db()
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = session['username'] + '_' + file.filename
            filename = secure_filename(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            query = 'insert into books (owner, title) values (?, ?)'
            title = file.filename
            with Image(filename="uploads/" + filename + "[0]") as img:
                img.save(filename="static/covers/" + filename + "_cover.jpg")
            db.execute(query, [session['username'], title])
            db.commit()
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return render_template('add_book.html')


@app.route('/log_out')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('login'))
