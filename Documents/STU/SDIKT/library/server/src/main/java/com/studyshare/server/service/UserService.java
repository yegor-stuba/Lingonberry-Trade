package com.studyshare.server.service;

import com.studyshare.common.dto.UserDTO;
import java.util.List;
import java.util.concurrent.CompletableFuture;

public interface UserService {
    UserDTO createUser(UserDTO userDTO);
    UserDTO getUserById(Long id);
    List<UserDTO> getAllUsers();
    UserDTO updateUser(Long id, UserDTO userDTO);
    void deleteUser(Long id);
    UserDTO findByUsername(String username);
    CompletableFuture<Boolean> login(String username, String password);
    CompletableFuture<UserDTO> register(UserDTO userDTO);
    CompletableFuture<UserDTO> getCurrentUser();
    CompletableFuture<Void> logout();
}