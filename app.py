# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load initial data from JSON files
with open('data.json', 'r') as file:
    data = json.load(file)

# Check if users.json is empty, initialize with an empty list if needed
try:
    with open('users.json', 'r') as file:
        users_data = json.load(file)
except json.decoder.JSONDecodeError:
    users_data = {"users": []}

# Helper function to save data to JSON files
def save_data():
    with open('data.json', 'w') as file:
        json.dump(data, file, indent=2)

    with open('users.json', 'w') as file:
        json.dump(users_data, file, indent=2)

# Helper function to get book by ID
def get_book_by_id(book_id):
    return next((book for book in data['books'] if book['id'] == book_id), None)

# Helper function to get user by ID
def get_user_by_id(user_id):
    return next((user for user in users_data['users'] if user['id'] == user_id), None)


# Route for home page - list of books with search functionality
@app.route('/')
def home():
    search_query = request.args.get('search', '')
    filtered_books = [book for book in data['books'] if search_query.lower() in book['title'].lower()]
    return render_template('home.html', books=filtered_books, search_query=search_query, user_id=session.get('user_id'))

# Route for individual book view
@app.route('/book/<int:book_id>')
def book_view(book_id):
    book = next((book for book in data['books'] if book['id'] == book_id), None)
    user_id = session.get('user_id')
    user = next((user for user in users_data['users'] if user['id'] == user_id), None) if user_id else None

    # Check if the book is borrowed by the signed-in user
    book_is_borrowed = any(issued_book['book_id'] == book_id and user_id == user['id'] for issued_book in user['issued_books'])
    borrowed_date = next((issued_book['borrow_date'] for issued_book in user['issued_books'] if issued_book['book_id'] == book_id), None)

    # Check book availability
    book_available = book['available'] > 0

    return render_template('book_view.html', book=book, user=user, book_is_borrowed=book_is_borrowed, borrowed_date=borrowed_date, book_available=book_available)


# Route for user profile page
@app.route('/profile/<int:user_id>')
def user_profile(user_id):
    user = next((user for user in users_data['users'] if user['id'] == user_id), None)
    return render_template('user_profile.html', user=user, data=data)  # Pass 'user' and 'data' variables

# Route for signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        if name and password:
            if users_data['users']:
                user_id = max(users_data['users'], key=lambda x: x['id'])['id'] + 1
            else:
                user_id = 1

            users_data['users'].append({
                'id': user_id,
                'name': name,
                'password': password,
                'issued_books': []
            })

            flash('Signup successful! Please signin.', 'success')
            save_data()
            return redirect(url_for('signin'))

        flash('Invalid signup details. Please try again.', 'danger')

    return render_template('signup.html')

# Route for signin
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        user = next((user for user in users_data['users'] if user['name'] == name and user['password'] == password), None)

        if user:
            session['user_id'] = user['id']
            flash('Signin successful!', 'success')
            return redirect(url_for('home'))

        flash('Invalid signin credentials. Please try again.', 'danger')

    return render_template('signin.html')

# Route for signout
@app.route('/signout')
def signout():
    session.pop('user_id', None)
    flash('Signout successful!', 'success')
    return redirect(url_for('home'))

# Route for borrowing a book
@app.route('/borrow/<int:book_id>')
def borrow_book(book_id):
    if 'user_id' not in session:
        flash('Please signin to borrow a book.', 'danger')
        return redirect(url_for('signin'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)
    book = get_book_by_id(book_id)

    if user and book and book['available'] > 0:
        # Check if the user has already borrowed the maximum allowed books
        if len(user['issued_books']) < data['max_books_per_user']:
            # Update book and user data
            book['available'] -= 1
            user['issued_books'].append({
                'book_id': book_id,
                'borrow_date': datetime.now().strftime('%Y-%m-%d')
            })

            flash('Book borrowed successfully!', 'success')
        else:
            flash('You have reached the maximum limit of borrowed books.', 'danger')
    elif book and book['available'] == 0:
        flash('All copies of this book are currently borrowed. Please try again later.', 'danger')
    else:
        flash('Book or user not found.', 'danger')

    save_data()
    return redirect(url_for('home'))

# Route for returning a book
@app.route('/return/<int:book_id>')
def return_book(book_id):
    if 'user_id' not in session:
        flash('Please signin to return a book.', 'danger')
        return redirect(url_for('signin'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)
    book = get_book_by_id(book_id)

    if user and book_id in [item['book_id'] for item in user['issued_books']]:
        # Update book and user data
        book['available'] += 1
        user['issued_books'] = [item for item in user['issued_books'] if item['book_id'] != book_id]

        flash('Book returned successfully!', 'success')
    else:
        flash('Book not found, not borrowed, or not issued by the current user.', 'danger')

    save_data()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
