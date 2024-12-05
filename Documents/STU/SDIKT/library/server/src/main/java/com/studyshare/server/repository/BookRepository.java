package com.studyshare.server.repository;

import com.studyshare.server.model.Book;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface BookRepository extends JpaRepository<Book, Long> {
    List<Book> findByOwnerId(Long ownerId);
    List<Book> findByTitleContainingIgnoreCase(String title);
    Optional<Book> findByIsbn(String isbn);
}