from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextField
from wtforms.validators import InputRequired, Length, Email, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[InputRequired(), Email(message=None),
                    Length(min=6, max=40)]
    )
    username = StringField(
        'Username',
        validators=[InputRequired(), Length(min=3, max=25)]
    )
    password = PasswordField(
        'Password',
        validators=[InputRequired(), Length(min=5, max=25)]
    )
    confirm = PasswordField(
        'Confirm password',
        validators=[
            InputRequired(), EqualTo('password', message='Passwords must match.')
        ]
    )
    submit = SubmitField('Register')
