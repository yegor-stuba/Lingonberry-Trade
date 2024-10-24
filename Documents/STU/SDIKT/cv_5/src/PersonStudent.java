// PersonStudent.java
class Person {
    protected String name;
    protected int age;

    // Constructor for Person
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    // Method to get the description of the person
    public String getDescription() {
        return "Name: " + name + ", Age: " + age;
    }
}

class Student extends Person {
    private String studentID;

    // Constructor for Student
    public Student(String name, int age, String studentID) {
        super(name, age);
        this.studentID = studentID;
    }

    // Override the getDescription method
    @Override
    public String getDescription() {
        return super.getDescription() + ", Student ID: " + studentID;
    }
}
