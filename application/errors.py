from flask import render_template, make_response, jsonify
from application import app, db


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# if Json only, ie RESTFUL Api
# @app.errorhandler(404)
# def not_found(error):
#     return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def not_found_error(error):
    return render_template('404.html'), 400


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
