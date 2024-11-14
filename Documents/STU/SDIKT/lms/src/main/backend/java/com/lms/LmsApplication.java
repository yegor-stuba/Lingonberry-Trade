package com.lms;

import java.util.Arrays;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import com.lms.entity.Author;
import com.lms.entity.Book;
import com.lms.entity.Category;
import com.lms.entity.Publisher;
import com.lms.entity.Role;
import com.lms.entity.User;
import com.lms.repository.UserRepository;
import com.lms.service.BookService;

@SpringBootApplication
public class LmsApplication {

    @Autowired
    private BCryptPasswordEncoder passwordEncoder;

    @Autowired
    private BookService bookService;

    @Autowired
    private UserRepository userRepository;

    public static void main(String[] args) {
        SpringApplication.run(LmsApplication.class, args);
    }

    @Bean
    public CommandLineRunner initialCreate() {
        return (args) -> {

            var book = new Book("AP1287", "Spring in Action ", "CXEF12389", "Book description");
            book.addAuthors(new Author("Matt", "dummy description"));
            book.addCategories(new Category("Dummy categary"));
            book.addPublishers(new Publisher("Dummy publisher"));
            bookService.createBook(book);

            var book1 = new Book("BP567#R", "Spring Microservices", "KCXEF12389", "Description1");
            book1.addAuthors(new Author("Maxwell", "Test description1"));
            book1.addCategories(new Category("New category"));
            book1.addPublishers(new Publisher("publisher2"));
            bookService.createBook(book1);

            var book2 = new Book("GH67F#", "Spring Boot", "UV#JH", "description2");
            book2.addAuthors(new Author("Josh Lang", "Test description2"));
            book2.addCategories(new Category("Spring category"));
            book2.addPublishers(new Publisher("publisher3"));
            bookService.createBook(book2);

            var user = new User("admin", "admin", "admin@admin.in", passwordEncoder.encode("Temp123"),
                    Arrays.asList(new Role("ROLE_ADMIN")));
            userRepository.save(user);

        };
    }
}
