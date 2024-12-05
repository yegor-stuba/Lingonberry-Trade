package com.studyshare.server.service;

import com.studyshare.common.dto.TransactionDTO;
import java.util.List;

public interface TransactionService {
    TransactionDTO createTransaction(TransactionDTO transactionDTO);
    TransactionDTO getTransactionById(Long id);
    List<TransactionDTO> getUserTransactions(Long userId);
    List<TransactionDTO> getBookTransactions(Long bookId);
    void completeTransaction(Long id);
}