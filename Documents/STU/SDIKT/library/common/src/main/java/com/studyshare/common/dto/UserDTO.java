package com.studyshare.common.dto;

import com.studyshare.common.enums.UserRole;
import lombok.Data;

@Data
public class UserDTO {
    private Long userId;
    private String username;
    private String email;
    private UserRole role;
    private String password; // Only used for registration/login
}