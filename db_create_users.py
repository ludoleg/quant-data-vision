from application import db
from application.models import User

# delete data
object = User.query.filter_by(name='ludo').first()
# object = User.query.filter(User.name == "Picsou")
db.session.delete(object)

# db.session.query.filter(name='donald').delete()
# db.session.query.filter(name='mike').delete()
# db.session.query.filter(name='Picsou').delete()
# db.session.query.filter(name='Brady').delete()
# db.session.query.filter(name='phil').delete()

# commit the changes
db.session.commit()
