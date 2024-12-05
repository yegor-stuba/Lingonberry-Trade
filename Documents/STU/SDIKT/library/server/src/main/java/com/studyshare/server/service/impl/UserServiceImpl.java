package com.studyshare.server.service.impl;

import com.studyshare.common.dto.UserDTO;
import com.studyshare.server.model.User;
import com.studyshare.server.repository.UserRepository;
import com.studyshare.server.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public UserDTO createUser(UserDTO userDTO) {
        User user = new User();
        user.setUsername(userDTO.getUsername());
        user.setEmail(userDTO.getEmail());
        user.setPassword(passwordEncoder.encode(userDTO.getPassword()));
        user.setRole(userDTO.getRole());
        return convertToDTO(userRepository.save(user));
    }

    @Override
    public UserDTO getUserById(Long id) {
        return userRepository.findById(id)
                .map(this::convertToDTO)
                .orElseThrow(() -> new RuntimeException("User not found"));
    }

    @Override
    public List<UserDTO> getAllUsers() {
        return userRepository.findAll().stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
    }

    @Override
    public UserDTO updateUser(Long id, UserDTO userDTO) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("User not found"));

        user.setEmail(userDTO.getEmail());
        if (userDTO.getPassword() != null) {
            user.setPassword(passwordEncoder.encode(userDTO.getPassword()));
        }
        user.setRole(userDTO.getRole());

        return convertToDTO(userRepository.save(user));
    }

    @Override
    public void deleteUser(Long id) {
        userRepository.deleteById(id);
    }

    @Override
    public UserDTO findByUsername(String username) {
        return userRepository.findByUsername(username)
                .map(this::convertToDTO)
                .orElseThrow(() -> new RuntimeException("User not found"));
    }

    @Override
    public CompletableFuture<Boolean> login(String username, String password) {
        return null;
    }

    @Override
    public CompletableFuture<UserDTO> register(UserDTO userDTO) {
        return null;
    }

    @Override
    public CompletableFuture<UserDTO> getCurrentUser() {
        return null;
    }

    @Override
    public CompletableFuture<Void> logout() {
        return null;
    }

    private UserDTO convertToDTO(User user) {
        UserDTO dto = new UserDTO();
        dto.setUserId(user.getUserId());
        dto.setUsername(user.getUsername());
        dto.setEmail(user.getEmail());
        dto.setRole(user.getRole());
        return dto;
    }
}