#################
#### imports ####
#################
from flask import flash, redirect, render_template, request, url_for, Blueprint, session
from flask_login import login_user, login_required, logout_user, current_user
from forms import LoginForm, RegisterForm
from application.models import User, bcrypt
from application import db

################
#### config ####
################

users_blueprint = Blueprint(
    'users', __name__,
    template_folder='templates'
)

################
#### routes ####
################
# route for handling the login page logic


@users_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = LoginForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(name=request.form['username']).first()
            if user is not None and bcrypt.check_password_hash(
                user.password, request.form['password']
            ):
                # session['logged_in'] = True
                login_user(user)
                # flash('You were logged in. Go Crazy.')
                return redirect(url_for('home'))

            else:
                error = 'Invalid username or password.'
    return render_template('login.html', form=form, error=error)


@users_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    # flash('You were logged out.')
    return redirect(url_for('home'))


@users_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('home'))
    return render_template('register.html', form=form)
