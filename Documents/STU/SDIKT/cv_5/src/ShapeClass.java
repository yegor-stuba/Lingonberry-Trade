// ShapeClasses.java
abstract class Shape {
    // Abstract method to calculate area
    public abstract double calculateArea();
}

class Circle extends Shape {
    private double radius;

    // Constructor for Circle
    public Circle(double radius) {
        this.radius = radius;
    }

    // Override calculateArea method
    @Override
    public double calculateArea() {
        return Math.PI * radius * radius;
    }
}

class Rectangle extends Shape {
    private double width;
    private double height;

    // Constructor for Rectangle
    public Rectangle(double width, double height) {
        this.width = width;
        this.height = height;
    }

    // Override calculateArea method
    @Override
    public double calculateArea() {
        return width * height;
    }
}

class Square extends Shape {
    private double side;

    // Constructor for Square
    public Square(double side) {
        this.side = side;
    }

    // Override calculateArea method
    @Override
    public double calculateArea() {
        return side * side;
    }
}
