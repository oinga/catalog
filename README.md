## Udacity Catalog Project README ##

![alt text](https://i.ibb.co/s9BZDsw/Cuisine-list.png)

- This is a flask application that will start a webserver serving at Localhost:8000
- Data is STORED in an "SqLite" database hosted on the local machine
- Users can login via OAuth2.0 using Google Api.
- Once logged in, users can perform CRUD operations via the frontend functions created by the flask framework.


## Dependencies ##

- Virutal Machine (Virtualbox)
    - https://www.virtualbox.org/wiki/Downloads
    - Install the appropriate platform package for your operating system.
- Vagrant
    - Vagrant is a software that configures a Virtual machine (VM) and lets you share files between your host computer and the VM's filesystem.
    - https://www.vagrantup.com/downloads.html
    - Install the appropriate platform package for your operating system.
    - Windows users: The Installer may request you grant network permissions to Vagrant or make a firewall exception(s). Please allow this request.

## How to the Start Application ##

1. Via Command Line, navigate to the root directory of this git repo (where the Vagrantfile is)
2. Execute "vagrant up && vagrant ssh". This will initialize, and boot you into your virtual environment.
    - Wait till execution finishes, and you have command prompt control again.
3. Execute "cd /vagrant".
4. Run 'python database_setup.py'.
5. Run 'python run.py'.
6. Visit localhost:8000 on a web browser on same machine to visit Item Catalog.


## The Design ##

- The database backend is made from sqlite, the database is mapped to ORM, using SQLAlchemy
- The framework is made with flask.
- It follows the PEP8 style guide.
- JSON rawdata is in url format, suffixed with "JSON" for the respective navigation URL. (e.g http://localhost:8000/cuisine JSON's at http://localhost:8000/cuisine/JSON)
