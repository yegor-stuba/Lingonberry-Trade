// AnimalClasses.java
abstract class Animal {
    // Abstract method to make sound
    public abstract void makeSound();
}

class Dog extends Animal {
    // Override makeSound method
    @Override
    public void makeSound() {
        System.out.println("Bark");
    }
}

class Cat extends Animal {
    // Override makeSound method
    @Override
    public void makeSound() {
        System.out.println("Meow");
    }
}
