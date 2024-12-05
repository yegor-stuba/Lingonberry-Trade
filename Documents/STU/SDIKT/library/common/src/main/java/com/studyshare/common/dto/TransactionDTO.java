package com.studyshare.common.dto;

import com.studyshare.common.enums.TransactionType;
import lombok.Data;
import java.time.LocalDateTime;

@Data
public class TransactionDTO {
    private Long transactionId;
    private Long userId;
    private Long bookId;
    private TransactionType type;
    private LocalDateTime date;
    private LocalDateTime dueDate;
}