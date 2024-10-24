// Main.java
public class Main {
    public static void main(String[] args) {
        // Task 1: Person and Student
        System.out.println("Task 1: Person and Student");
        Person person = new Person("Alice", 30);
        Student student = new Student("Bob", 20, "S12345");
        System.out.println(person.getDescription());
        System.out.println(student.getDescription());
        System.out.println("\n----------------------\n");

        // Task 2: Shape Polymorphism
        System.out.println("Task 2: Shape Polymorphism");
        Shape circle = new Circle(5.0);
        Shape rectangle = new Rectangle(4.0, 6.0);
        Shape square = new Square(3.0);
        System.out.println("Circle area: " + circle.calculateArea());
        System.out.println("Rectangle area: " + rectangle.calculateArea());
        System.out.println("Square area: " + square.calculateArea());
        System.out.println("\n----------------------\n");

        // Task 3: Printer Overloading and Figure Runtime Polymorphism
        System.out.println("Task 3_1: Printer Overloading");
        Printer printer = new Printer();
        printer.print("Hello, World!");
        printer.print(123);
        System.out.println("\n----------------------\n");

        System.out.println("Task 3_2: Runtime Polymorphism with Figures");
        Figure polygon = new Polygon();
        Figure octagon = new Octagon();
        polygon.draw();
        octagon.draw();
        System.out.println("\n----------------------\n");

        // Task 4: Animal Polymorphism
        System.out.println("Task 4: Animal Polymorphism");
        Animal dog = new Dog();
        Animal cat = new Cat();
        dog.makeSound();
        cat.makeSound();
    }
}
