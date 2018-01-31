#################
#### imports ####
#################
from flask import flash, redirect, render_template, request, url_for, Blueprint, session
from werkzeug.urls import url_parse
from flask_login import login_user, login_required, logout_user, current_user
from forms import LoginForm, RegisterForm
from application.models import User
from application import db, bcrypt

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
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('users.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@users_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    # flash('You were logged out.')
    return redirect(url_for('home'))


@users_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.username.data, email=form.email.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)
