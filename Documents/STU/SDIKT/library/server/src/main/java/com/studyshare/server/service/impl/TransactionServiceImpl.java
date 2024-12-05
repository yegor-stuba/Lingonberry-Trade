package com.studyshare.server.service.impl;

import com.studyshare.common.dto.TransactionDTO;
import com.studyshare.server.model.Transaction;
import com.studyshare.server.repository.TransactionRepository;
import com.studyshare.server.repository.BookRepository;
import com.studyshare.server.repository.UserRepository;
import com.studyshare.server.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class TransactionServiceImpl implements TransactionService {
    private final TransactionRepository transactionRepository;
    private final UserRepository userRepository;
    private final BookRepository bookRepository;

    @Override
    public TransactionDTO createTransaction(TransactionDTO transactionDTO) {
        Transaction transaction = new Transaction();
        transaction.setUser(userRepository.findById(transactionDTO.getUserId())
                .orElseThrow(() -> new RuntimeException("User not found")));
        transaction.setBook(bookRepository.findById(transactionDTO.getBookId())
                .orElseThrow(() -> new RuntimeException("Book not found")));
        transaction.setType(transactionDTO.getType());
        transaction.setDate(transactionDTO.getDate());
        transaction.setDueDate(transactionDTO.getDueDate());

        return convertToDTO(transactionRepository.save(transaction));
    }

    @Override
    public TransactionDTO getTransactionById(Long id) {
        return transactionRepository.findById(id)
                .map(this::convertToDTO)
                .orElseThrow(() -> new RuntimeException("Transaction not found"));
    }

    @Override
    public List<TransactionDTO> getUserTransactions(Long userId) {
        return transactionRepository.findByUserId(userId).stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
    }

    @Override
    public List<TransactionDTO> getBookTransactions(Long bookId) {
        return transactionRepository.findByBookId(bookId).stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
    }

    @Override
    public void completeTransaction(Long id) {
        Transaction transaction = transactionRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Transaction not found"));
        // Add logic for completing transaction
        transactionRepository.save(transaction);
    }

    private TransactionDTO convertToDTO(Transaction transaction) {
        TransactionDTO dto = new TransactionDTO();
        dto.setTransactionId(transaction.getTransactionId());
        dto.setUserId(transaction.getUser().getUserId());
        dto.setBookId(transaction.getBook().getBookId());
        dto.setType(transaction.getType());
        dto.setDate(transaction.getDate());
        dto.setDueDate(transaction.getDueDate());
        return dto;
    }
}