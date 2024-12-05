package com.studyshare.common.dto;

import lombok.Data;

@Data
public class BookDTO {
    private Long bookId;
    private String title;
    private String author;
    private String isbn;
    private Integer availableCopies;
    private Long ownerId;
}