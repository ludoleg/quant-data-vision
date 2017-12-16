from application import db
from application.models import User

# insert data
db.session.add(User("admin", "ad@min.com", "admin"))
db.session.add(User("ludo", "ludoleg@pacbell.net", "ludo"))

# commit the changes
db.session.commit()
