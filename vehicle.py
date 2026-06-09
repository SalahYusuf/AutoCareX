from flask import Flask, render_template,request,redirect
import json
import os

app = Flask(__name__)

DATA_FILE = os.path.join("data","cars.json")

#loading car#
def load_cars():
    try:
        with open(DATA_FILE,"r") as f:
            return json.load(f)
    except:
        return []
    
#make new changes#   
def save_cars(cars):
    with open(DATA_FILE,"w") as f:
        json.dump(cars,f)

#html link transfer#
@app.route("/")
def home():
    return render_template("Home.html")

@app.route("/vehicle")
def vehicle():

    cars = load_cars()

    image_map = {
        "EMAS 5": "/static/image/emas5.jpg",
        "EMAS 7": "/static/image/emas7.jpg",
        "EMAS PHEV": "/static/image/emasphev.jpg"
    }

    for car in cars:
        car["image"] = image_map.get(car["model"],"")

    first_car = cars[0] if cars else None

    return render_template(
        "vehicle.html",
        cars=cars,
        car_count=len(cars),
        first_car=first_car
    )

@app.route("/add_car",methods=["POST"])
def add_car():

    cars = load_cars()

    nickname = request.form["nickname"]
    year = request.form["year"]
    model = request.form["model"]

    new_car = {
        "nickname":nickname,
        "year":year,
        "model":model
    }

    cars.append(new_car)
    save_cars(cars)
    
    return redirect("/vehicle")

@app.route("/location")
def location():
    return render_template("location.html")

@app.route("/upgrade")
def upgrade():
    return render_template("upgrade.html")

if __name__ == "__main__":
    app.run(debug=True)