// FigureClasses.java
abstract class Figure {
    // Abstract method to draw the figure
    public abstract void draw();
}

class Polygon extends Figure {
    // Override draw method
    @Override
    public void draw() {
        System.out.println("Drawing a polygon");
    }
}

class Octagon extends Figure {
    // Override draw method
    @Override
    public void draw() {
        System.out.println("Drawing an octagon");
    }
}
