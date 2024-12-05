package com.studyshare.client.controller;

import com.studyshare.client.service.UserService;
import javafx.fxml.FXML;
import javafx.scene.control.TextField;
import javafx.scene.control.PasswordField;
import org.springframework.stereotype.Controller;

@Controller
public class LoginController {

    private final UserService userService;

    public LoginController(UserService userService) {
        this.userService = userService;
    }

    @FXML
    private TextField usernameField;

    @FXML
    private PasswordField passwordField;

    @FXML
    private void handleLogin() {
        String username = usernameField.getText();
        String password = passwordField.getText();

        userService.login(username, password)
            .thenAccept(success -> {
                if (Boolean.TRUE.equals(success)) {
                    // Navigate to main view
                } else {
                    // Show error
                }
            });
    }
}