# 🤝 Contributing to AI System Optimizer Assistant

First off, thank you for considering contributing to this project! It's people like you who make the open-source community such an amazing place to learn, inspire, and create.

## ⚖️ Ownership & Author Integrity (STRICT RULE)
This project is authored and owned by **Mohammad Quasif**. 
- **Attribution**: You are **NOT** permitted to remove, modify, or obscure the author/owner details in the code headers, README, or App Metadata.
- **Credit**: If you contribute, your name will be added to a "Contributors" list, but the primary authorship remains with the original creator.

## 🚀 How to Contribute
To ensure the stability of the `main` branch, we use the **Fork & Pull Request** model:

1. **Fork the Repository**: Create your own copy of the project on GitHub.
2. **Create a Branch**: Work on a descriptive branch name (e.g., `fix-memory-leak` or `feat-dark-mode`).
3. **Commit Your Changes**: Keep your commits clean and descriptive.
4. **Push to Your Fork**: Upload your changes to your own GitHub copy.
5. **Submit a Pull Request (PR)**: Target the `main` branch of the original repository. 

## 🛡️ Protecting the Main Codebase
- **No Direct Pushes**: Direct pushes to the `main` branch are restricted. All changes must go through a PR.
- **Review Process**: The owner will review every PR for:
    - Thread safety (PyQt6 requires UI updates on the main thread).
    - Performance impact (Zero background RAM usage is a core goal).
    - Privacy (No external tracking or data collection).
- **Code Style**: Maintain the "Cyberpunk/Glassmorphism" aesthetic for all UI changes.

## 🛡️ Security & Protection Policy
To maintain 100% codebase integrity, this repository is protected by the following GitHub rules:
1. **Require Pull Requests**: Direct pushes to `main` are disabled.
2. **Mandatory Approvals**: All code changes require at least **one approval** from the owner (**Mohammad Quasif**) before merging.
3. **Branch Protection**: GitHub literally blocks any merge that doesn't meet these criteria, protecting the project from unauthorized or accidental breaking changes.

## 🛠️ Development Guidelines
- **Thread Safety**: Always use `QThread` and `pyqtSignal` for long-running tasks.
- **Local AI**: All AI features must use the `AIService` abstraction and support local providers like Ollama.
- **Documentation**: Update the README if your change adds new user-facing features or commands.

## 📜 License
By contributing, you agree that your contributions will be licensed under the project's existing [LICENSE](LICENSE).

---
*Thank you for helping make Windows optimization smarter and more accessible!*
