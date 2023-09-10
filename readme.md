# Kreo Classic

Kreo Classic is a market maker application on [Injective](http://https://injective.com/ "Injective") Exchange that uses Injective DMM plan's contribution parameters for its strategy. 

## Set Up
In order to use this application, first of all, you need to clone this repository in your server or local machine. 
```bash
git clone https://github.com/LovitaResearchTeam/classic-kreo.git
```
Then copy the directory `settings.example/` into a new directory named `settings/`:
```bash
cp -r settings.example/ settings
```
Now you can go in this directory and set all the settings you want to use in the application.

Note that in order to run this application you need to install all requirements specified in file `requirements.txt`. To do so, create a python virtual environmet with python 3.10+ and activate it, then run below command:
```bash
pip install -r requirements.txt
```
You also need to install two major requirements, `redis` and `pm2` on your system.

## Launch
To launch the application, use below command.
```bash
python main.py [market0] [market1] [market2] ...
```
Note that each market uses different wallets that you specified in your settings, respectively.