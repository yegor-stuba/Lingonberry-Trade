package com.studyshare.client.service;

import com.studyshare.common.dto.UserDTO;
import java.util.concurrent.CompletableFuture;

public interface UserService {
    CompletableFuture<Boolean> login(String username, String password);
    CompletableFuture<UserDTO> register(UserDTO userDTO);
    CompletableFuture<UserDTO> getCurrentUser();
    CompletableFuture<Void> logout();
}