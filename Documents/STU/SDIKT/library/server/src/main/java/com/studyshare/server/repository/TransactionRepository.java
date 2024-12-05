package com.studyshare.server.repository;

import com.studyshare.server.model.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface TransactionRepository extends JpaRepository<Transaction, Long> {
    List<Transaction> findByUserId(Long userId);
    List<Transaction> findByBookId(Long bookId);
    List<Transaction> findByUserIdAndBookId(Long userId, Long bookId);
}