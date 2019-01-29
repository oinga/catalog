from flask import Flask, render_template, request, redirect,jsonify, url_for, flash

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Cuisine, Restaurant, MenuItem, User

#Auth2.0 imports
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']



#Connect to Database and create database session
engine = create_engine('sqlite:///foodiecatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#------------------------------- BEGIN JSON ROUTES -----------------------------
#JSON to view Cuisines
@app.route('/cuisine/JSON')
def cuisinesJSON():
    cuisines = session.query(Cuisine).all()
    return jsonify(cuisines= [c.serialize for c in cuisines])

#JSON to view Restaurant Menus
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

#JSON to view Restaurant Menu Information
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    Menu_Item = session.query(MenuItem).filter_by(id = menu_id).one()
    return jsonify(Menu_Item = Menu_Item.serialize)

#JSON to view Restaurant
@app.route('/restaurant/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants= [r.serialize for r in restaurants])

#--------------------------------END JSON ROUTES -------------------------------

#-----------------------------BEGIN LOGIN ROUTES -------------------------------

@app.route('/login/')
def showLogin():
    # Create anti-forgery state token
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    print(h.request(url, 'GET')[1])
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                'Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        login_session['user_id'] = getUserID(login_session['email'])
        flash("You are logged in as %s" % login_session['username'])
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # Add user id to DB if not in DB already, and add id to login_session
    user_id = getUserID(data['email'])
    if not user_id:
        added_user_id = createUser(login_session)
        login_session['user_id'] = added_user_id
    else:
        login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += (' " style = "width: 300px; height: 300px;border-radius: 150px;'
               '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> ')
    flash("You are now logged in as %s" % login_session['username'])
    print("done!")
    return output

# User Helper Functions

# takes in session and creates user extracting all fields with info provide
# Then
def createUser(login_session):
    session = DBSession()
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    session = DBSession()
    return session.query(User).filter_by(id=user_id).one()


def getUserID(email):
    session = DBSession()
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception:
        return None

#-----------------------------END LOG IN ROUTES -------------------------------

#-----------------------------BEGIN LOG OUT ROUTES -----------------------------

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print("Access Token is None")
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print("In gdisconnect access token is %s" % (access_token))
    print("User name is: ")
    print(login_session['username'])
    url = "https://accounts.google.com/o/oauth2/revoke?token={}" \
        .format(login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print("result is ")
    print(result)
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        error_string = "Failed to revoke token for given user."
        response = make_response(json.dumps(error_string), 400)
        response.headers['Content-Type'] = "application/json"
        return response

#-----------------------------END LOG OUT ROUTES -------------------------------


#-----------------------------BEGIN CUISINE ROUTES -----------------------------

# Show public cuisine details (need to add details)
#@app.route('/allcuisine/<int:id>/')
#def show_publiccuisine(id):
#    cuisine = session.query(Cuisine).filter_by(id = id).one()
#    return render_template('publiccuisines.html', cuisine = cuisine)

#Show all cuisines public
@app.route('/')
@app.route('/home/public/')
def showCuisines():
  cuisines = session.query(Cuisine).order_by(asc(Cuisine.name))
  return render_template('publiccuisines.html', cuisines = cuisines)

# Show all cuisines private
@app.route('/cuisines/')
def show_myCuisines():
  if 'username' not in login_session:
      return redirect('login')
      flash('You must sign in to add a new cuisine')
  cuisines = session.query(Cuisine).order_by(asc(Cuisine.name))
  return render_template('cuisines.html', cuisines = cuisines)

# Show public cuisine details
@app.route('/cuisine/public/<int:id>/')
def publiccuisineDetails(id):
      cuisine = session.query(Cuisine).filter_by(id = id).one()
      return render_template('publiccuisineDetails.html', cuisine = cuisine)

# Show public cuisine details
@app.route('/cuisine/<int:id>/')
def cuisineDetails(id):
      cuisine = session.query(Cuisine).filter_by(id = id).one()
      return render_template('cuisineDetails.html', cuisine = cuisine)

#Create a new cuisine
@app.route('/cuisine/new/', methods=['GET','POST'])
def newCuisine():
  if 'username' not in login_session:
      return redirect('login')
      flash('You must sign in to add a new cuisine')
  if request.method == 'POST':
      newCuisine = Cuisine(name = request.form['name'], description =  request.form['description'], user_id=login_session['user_id'])
      session.add(newCuisine)
      flash('New Cuisine %s Successfully Created' % newCuisine.name)
      session.commit()
      return redirect(url_for('show_myCuisines'))
  else:
      return render_template('newCuisine.html')

#Edit a cuisine
@app.route('/cuisine/<int:id>/edit/', methods = ['GET', 'POST'])
def editCuisine(id):
  if 'username' not in login_session:
      return redirect('login')
  editedCuisine = session.query(Cuisine).filter_by(id = id).one()
  if editedCuisine.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized"\
         "to edit this item. Please create your own item in order to edit.');"\
"window.location = '/cuisines';}</script><body onload='myFunction()''>"
  if request.method == 'POST':
      if request.form['name']:
        editedCuisine.name = request.form['name']
      if request.form['description']:
        editedCuisine.description = request.form['description']
        flash('Cuisine Successfully Edited %s' % editedCuisine.name)
        return redirect(url_for('show_myCuisines'))
  else:
    return render_template('editCuisine.html', cuisine = editedCuisine)

#Delete a cuisine
@app.route('/cuisine/<int:id>/delete/', methods = ['GET','POST'])
def deleteCuisine(id):
  if 'username' not in login_session:
      return redirect('login')
  cuisineToDelete = session.query(Cuisine).filter_by(id = id).one()
  if cuisineToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized"\
         "to edit this. Please create your own item in order to edit.');"\
"window.location = '/cuisines';}</script><body onload='myFunction()''>"
  if request.method == 'POST':
    session.delete(cuisineToDelete)
    flash('%s Successfully Deleted' % cuisineToDelete.name)
    session.commit()
    return redirect(url_for('show_myCuisines', id = id))
  else:
    return render_template('deleteCuisine.html',cuisine = cuisineToDelete)

#-----------------------------END CUISINE ROUTES -------------------------------

#-----------------------------BEGIN RESTAURANT ROUTES --------------------------

#Show all  restaurants
@app.route('/')
@app.route('/restaurant/public/')
def showRestaurants():
  restaurants = session.query(Restaurant).order_by(asc(Restaurant.name))
  return render_template('publicrestaurants.html', restaurants = restaurants)

#Show all public restaurants
@app.route('/')
@app.route('/restaurant/')
def show_myRestaurants():
  restaurants = session.query(Restaurant).order_by(asc(Restaurant.name))
  return render_template('restaurants.html', restaurants = restaurants)

#Create a new restaurant
@app.route('/cuisine/restaurant/new/', methods=['GET','POST'])
def newRestaurant():
  if 'username' not in login_session:
      return redirect('login')
  if request.method == 'POST':
      newRestaurant = Restaurant(name = request.form['name'], user_id=login_session['user_id'])
      session.add(newRestaurant)
      flash('New Restaurant %s Successfully Created' % newRestaurant.name)
      session.commit()
      return redirect(url_for('show_myRestaurants'))
  else:
      return render_template('newRestaurant.html')

#Edit a restaurant
@app.route('/restaurant/<int:restaurant_id>/edit/', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
  if 'username' not in login_session:
      return redirect('login')
  editedRestaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
  if editedRestaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized"\
         "to edit this. Please create your own item in order to edit.');"\
"window.location = '/cuisines';}</script><body onload='myFunction()''>"
  if request.method == 'POST':
      if request.form['name']:
        editedRestaurant.name = request.form['name']
        flash('Restaurant Successfully Edited %s' % editedRestaurant.name)
        return redirect(url_for('showRestaurants'))
  else:
        return render_template('editRestaurant.html', restaurant = editedRestaurant)


#Delete a restaurant
@app.route('/restaurant/<int:restaurant_id>/delete/', methods = ['GET','POST'])
def deleteRestaurant(restaurant_id):
  if 'username' not in login_session:
      return redirect('login')
  restaurantToDelete = session.query(Restaurant).filter_by(id = restaurant_id).one()
  if restaurantToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized"\
         "to edit this. Please create your own item in order to edit.');"\
"window.location = '/cuisines';}</script><body onload='myFunction()''>"
  if request.method == 'POST':
    session.delete(restaurantToDelete)
    flash('%s Successfully Deleted' % restaurantToDelete.name)
    session.commit()
    return redirect(url_for('showRestaurants', restaurant_id = restaurant_id))
  else:
    return render_template('deleteRestaurant.html',restaurant = restaurantToDelete)

#----------------------------END RESTAURANT ROUTES -----------------------------


#-----------------------------BEGIN RESTAURANT MENU ROUTES ---------------------

#Show a public restaurant menu
@app.route('/restaurant/public/<int:restaurant_id>/')
@app.route('/restaurant/public/<int:restaurant_id>/menu/')
def show_publicMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    creator = getUserInfo(restaurant.user_id)
    return render_template('menupublic.html', items = items, restaurant = restaurant, creator = creator)

#Show a restaurant menu
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    return render_template('menu.html', items = items, restaurant = restaurant)



#Create a new menu item
@app.route('/restaurant/<int:restaurant_id>/menu/new/',methods=['GET','POST'])
def newMenuItem(restaurant_id):
  if 'username' not in login_session:
      return redirect('login')
  restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
  if request.method == 'POST':
      newItem = MenuItem(name = request.form['name'], description = request.form['description'], price = request.form['price'], course = request.form['course'], restaurant_id=restaurant_id, user_id=restaurant.user_id)
      session.add(newItem)
      session.commit()
      flash('New Menu %s Item Successfully Created' % (newItem.name))
      return redirect(url_for('showMenu', restaurant_id = restaurant_id))
  else:
      return render_template('newmenuitem.html', restaurant_id = restaurant_id)

#Edit a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
      return redirect('login')
    editedItem = session.query(MenuItem).filter_by(id = menu_id).one()
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    # If user not creator of item redirect
    if creator.id != login_session['user_id']:
      flash ("You cannot edit this. This belongs to %s" % creator.name)
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id = restaurant_id, menu_id = menu_id, item = editedItem)


#Delete a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', methods = ['GET','POST'])
def deleteMenuItem(restaurant_id,menu_id):
    if 'username' not in login_session:
      return redirect('login')
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    itemToDelete = session.query(MenuItem).filter_by(id = menu_id).one()
    creator = getUserInfo(restaurant.user_id)
  # If user not creator of item redirect
    if creator.id != login_session['user_id']:
      flash ("You cannot edit this. This belongs to %s" % creator.name)
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('deleteMenuItem.html', item = itemToDelete)
#-----------------------------END RESTAURANT MENU ROUTES ----------------------


if __name__ == '__main__':
  app.secret_key = 'guessworkz'
  app.debug = True # Disable in production
  app.run(host = '0.0.0.0', port = 5000)
