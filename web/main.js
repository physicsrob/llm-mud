document.addEventListener('DOMContentLoaded', () => {
    // Auth state
    let authToken = localStorage.getItem('auth_token');
    let username = localStorage.getItem('username');
    
    // Auth modal elements
    const authModal = document.getElementById('auth-modal');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const loginForm = document.getElementById('login-form-el');
    const registerForm = document.getElementById('register-form-el');
    const loginErrors = document.getElementById('login-errors');
    const registerErrors = document.getElementById('register-errors');
    const userDisplay = document.getElementById('user-display');
    const logoutBtn = document.getElementById('logout-btn');
    
    // Define terminal themes
    const themes = {
        dark: {
            background: '#000000',
            foreground: '#f0f0f0',
            cursor: '#f0f0f0',
            selection: 'rgba(255, 255, 255, 0.3)',
            black: '#000000',
            red: '#cc0000',
            green: '#4e9a06',
            yellow: '#c4a000',
            blue: '#3465a4',
            magenta: '#75507b',
            cyan: '#06989a',
            white: '#d3d7cf'
        },
        light: {
            background: '#ffffff',
            foreground: '#000000',
            cursor: '#000000',
            selection: 'rgba(0, 0, 0, 0.3)',
            black: '#000000',
            red: '#cc0000',
            green: '#4e9a06',
            yellow: '#c4a000',
            blue: '#3465a4',
            magenta: '#75507b',
            cyan: '#06989a',
            white: '#d3d7cf'
        },
        retro: {
            background: '#2b2b2b',
            foreground: '#00ff00',
            cursor: '#00ff00',
            selection: 'rgba(0, 255, 0, 0.3)',
            black: '#2b2b2b',
            red: '#ff5555',
            green: '#55ff55',
            yellow: '#ffff55',
            blue: '#5555ff',
            magenta: '#ff55ff',
            cyan: '#55ffff',
            white: '#f0f0f0'
        },
        matrix: {
            background: '#000000',
            foreground: '#00ff00',
            cursor: '#00ff00',
            selection: 'rgba(0, 255, 0, 0.3)',
            black: '#000000',
            red: '#008f11',
            green: '#00ff00',
            yellow: '#00df00',
            blue: '#00af00',
            magenta: '#008f00',
            cyan: '#005500',
            white: '#00ff00'
        }
    };
    
    // Initialize terminal
    const term = new Terminal({
        cursorBlink: true,
        theme: themes.dark,
        fontSize: 16,           // Medium font size
        fontWeight: 'normal',   // Options: 'normal', 'bold', etc.
        fontFamily: '"Source Code Pro", monospace',
        letterSpacing: 0,       // Can be adjusted for spacing
        lineHeight: 1.2,        // Can increase for better readability
        allowTransparency: true,
        cursorStyle: 'block',   // Options: 'block', 'underline', 'bar'
        cursorWidth: 2,
        scrollback: 1000        // Number of lines to keep in scrollback
    });
    
    // Create FitAddon from CDN
    const fitAddon = new (window.FitAddon.FitAddon)();
    term.loadAddon(fitAddon);
    
    // Open terminal in the container element
    term.open(document.getElementById('terminal'));
    
    // Fit terminal to container size
    fitAddon.fit();
    
    // Handle window resize
    window.addEventListener('resize', () => {
        fitAddon.fit();
    });
    
    // Setup font size control
    const fontSizeSelect = document.getElementById('font-size');
    fontSizeSelect.addEventListener('change', (e) => {
        const newSize = parseInt(e.target.value, 10);
        term.options.fontSize = newSize;
        fitAddon.fit();
    });
    
    // Setup font family control
    const fontFamilySelect = document.getElementById('font-family');
    fontFamilySelect.addEventListener('change', (e) => {
        const newFont = e.target.value;
        term.options.fontFamily = newFont;
        fitAddon.fit();
    });
    
    // Setup theme control
    const themeSelect = document.getElementById('theme');
    themeSelect.addEventListener('change', (e) => {
        const newTheme = e.target.value;
        term.options.theme = themes[newTheme];
        
        // Also update terminal container background to match
        const terminalElement = document.getElementById('terminal');
        terminalElement.style.backgroundColor = themes[newTheme].background;
    });

    // Variables to manage command input
    let commandBuffer = '';
    let commandHistory = [];
    let historyPosition = -1;
    
    // Tab switching functionality
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(`${tabId}-form`).classList.add('active');
        });
    });
    
    // Form submission handling
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginErrors.textContent = '';
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Store auth data
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('username', data.username);
                authToken = data.token;
                
                // Update UI
                authModal.classList.remove('active');
                userDisplay.textContent = data.username;
                logoutBtn.style.display = 'inline-block';
                
                // Connect to WebSocket with token
                connectWebSocket();
            } else {
                loginErrors.textContent = data.message || 'Invalid credentials';
            }
        } catch (error) {
            loginErrors.textContent = 'Server error. Please try again.';
        }
    });
    
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        registerErrors.textContent = '';
        
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const confirm = document.getElementById('register-confirm').value;
        
        if (password !== confirm) {
            registerErrors.textContent = 'Passwords do not match';
            return;
        }
        
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Store auth data
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('username', data.username);
                authToken = data.token;
                
                // Update UI
                authModal.classList.remove('active');
                userDisplay.textContent = data.username;
                logoutBtn.style.display = 'inline-block';
                
                // Connect to WebSocket with token
                connectWebSocket();
            } else {
                registerErrors.textContent = data.message || 'Registration failed';
            }
        } catch (error) {
            registerErrors.textContent = 'Server error. Please try again.';
        }
    });
    
    // Logout functionality
    logoutBtn.addEventListener('click', () => {
        // Clear auth data
        localStorage.removeItem('auth_token');
        localStorage.removeItem('username');
        authToken = null;
        
        // Update UI
        userDisplay.textContent = 'Not logged in';
        logoutBtn.style.display = 'none';
        
        // Disconnect and show login
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }
        
        authModal.classList.add('active');
    });
    
    // Connect to WebSocket server
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    let socket;
    let connected = false;
    
    function connectWebSocket() {
        // Don't connect if no auth token
        if (!authToken) {
            authModal.classList.add('active');
            return;
        }
        
        term.writeln('Connecting to server...');
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            connected = true;
            document.getElementById('connection-status').textContent = 'Connected';
            document.getElementById('connection-status').classList.add('connected');
            term.writeln('Connection established!');
            
            // Send auth token to server
            socket.send(authToken);
        };
        
        socket.onclose = () => {
            connected = false;
            document.getElementById('connection-status').textContent = 'Disconnected';
            document.getElementById('connection-status').classList.remove('connected');
            term.writeln('\r\nConnection closed. Attempting to reconnect in 5 seconds...');
            
            // Attempt to reconnect after 5 seconds
            setTimeout(connectWebSocket, 5000);
        };
        
        socket.onerror = (error) => {
            term.writeln(`\r\nWebSocket error: ${error.message}`);
        };
        
        socket.onmessage = (event) => {
            // Process incoming message
            const message = event.data;
            
            // Check if this is the welcome message with world title
            if (message.startsWith('Welcome to ')) {
                // Extract world title
                const worldTitle = message.split('!')[0].replace('Welcome to ', '');
                document.title = `${worldTitle} - LLM-MUD Terminal`;
            }
            
            // Split message by newlines and write each line
            const lines = message.split('\n');
            for (const line of lines) {
                term.writeln(`\r${line}`);
            }
            
            term.write('\r\n> ');
            commandBuffer = '';
        };
    }
    
    // Handle terminal input
    term.onKey(({ key, domEvent }) => {
        const printable = !domEvent.altKey && !domEvent.ctrlKey && !domEvent.metaKey;
        
        // Handle special keys
        if (domEvent.keyCode === 13) { // Enter key
            // Send command to server
            if (connected && commandBuffer.trim()) {
                socket.send(commandBuffer);
                commandHistory.push(commandBuffer);
                historyPosition = commandHistory.length;
            }
            term.write('\r\n');
            commandBuffer = '';
        } else if (domEvent.keyCode === 8) { // Backspace
            if (commandBuffer.length > 0) {
                commandBuffer = commandBuffer.substring(0, commandBuffer.length - 1);
                term.write('\b \b');
            }
        } else if (domEvent.keyCode === 38) { // Up arrow (history)
            if (historyPosition > 0) {
                historyPosition--;
                // Clear current line
                term.write('\r' + '> ' + ' '.repeat(commandBuffer.length) + '\r');
                term.write('> ');
                commandBuffer = commandHistory[historyPosition];
                term.write(commandBuffer);
            }
        } else if (domEvent.keyCode === 40) { // Down arrow (history)
            if (historyPosition < commandHistory.length - 1) {
                historyPosition++;
                // Clear current line
                term.write('\r' + '> ' + ' '.repeat(commandBuffer.length) + '\r');
                term.write('> ');
                commandBuffer = commandHistory[historyPosition];
                term.write(commandBuffer);
            } else if (historyPosition === commandHistory.length - 1) {
                historyPosition = commandHistory.length;
                // Clear current line
                term.write('\r' + '> ' + ' '.repeat(commandBuffer.length) + '\r');
                term.write('> ');
                commandBuffer = '';
            }
        } else if (printable) {
            commandBuffer += key;
            term.write(key);
        }
    });
    
    // Initialize with welcome message
    term.writeln('Welcome to LLM-MUD Terminal');
    term.writeln('Please log in to continue...');
    term.write('> ');
    
    // Check if user is already logged in
    if (authToken && username) {
        userDisplay.textContent = username;
        logoutBtn.style.display = 'inline-block';
        connectWebSocket();
    } else {
        // Show login modal
        authModal.classList.add('active');
    }
});