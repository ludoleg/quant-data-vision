from app import db
from models import Mode

# create the database and the db table
db.create_all()

# insert data
db.session.add(Mode("default", "rock"))
db.session.add(Mode("ludo", "pigment"))

# commit the changes
db.session.commit()
