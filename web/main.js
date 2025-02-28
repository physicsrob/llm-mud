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
        cursorStyle: 'underline', // Using underscore cursor
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
    
    // Auto-focus the terminal when the page loads
    term.focus();
    
    // Handle window resize
    window.addEventListener('resize', () => {
        fitAddon.fit();
    });
    
    // Re-focus terminal on window/document click
    document.addEventListener('click', () => {
        // Don't focus if clicking on modal or form elements
        const activeModals = document.querySelectorAll('.modal.active');
        if (activeModals.length === 0) {
            term.focus();
        }
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
    
    // Typewriter effect is enabled by default with constant speed

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
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            connected = true;
            document.getElementById('connection-status').textContent = 'Connected';
            document.getElementById('connection-status').classList.add('connected');
            
            // Send auth token to server
            socket.send(authToken);
            
            // Focus the terminal when the connection is established
            term.focus();
        };
        
        socket.onclose = () => {
            connected = false;
            document.getElementById('connection-status').textContent = 'Disconnected';
            document.getElementById('connection-status').classList.remove('connected');
            
            // Stop spinner if active when connection closes
            stopSpinner();
            
            term.writeln('\r\nConnection closed. Attempting to reconnect in 5 seconds...');
            
            // Attempt to reconnect after 5 seconds
            setTimeout(connectWebSocket, 5000);
        };
        
        socket.onerror = (error) => {
            // Stop spinner if active when error occurs
            stopSpinner();
            
            term.writeln(`\r\nWebSocket error: ${error.message}`);
        };
        
        // Message queue to handle messages in sequence
        let messageQueue = [];
        let processingMessages = false;
        
        // Function to handle typewriter effect with word-by-word animation
        async function typeWriter(text) {
            // Set typing speed (milliseconds per word)
            const TYPING_SPEED = 20;
            
            // Check if text is empty
            if (!text || text.length === 0) return;
            
            // Split text into lines
            const lines = text.split('\n');
            
            // Process each line
            for (let i = 0; i < lines.length; i++) {
                // Don't add extra linebreak for first line (we handle that elsewhere)
                if (i > 0) {
                    term.write('\r\n');
                }
                
                // Skip empty lines
                if (lines[i].length === 0) continue;
                
                // Split line into words
                const words = lines[i].split(' ');
                
                // Write words with delays
                for (let j = 0; j < words.length; j++) {
                    // Add space before words (except first word)
                    if (j > 0) {
                        term.write(' ');
                    }
                    
                    // Write the word
                    term.write(words[j]);
                    
                    // Add delay between words
                    await new Promise(resolve => setTimeout(resolve, TYPING_SPEED));
                }
            }
        }
        
        // Process messages one at a time from the queue
        async function processMessageQueue() {
            if (processingMessages || messageQueue.length === 0) return;
            
            processingMessages = true;
            
            while (messageQueue.length > 0) {
                const message = messageQueue.shift();
                
                // Set cursor to underscore and disable blinking during typing
                const originalCursorStyle = term.options.cursorStyle;
                const originalCursorBlink = term.options.cursorBlink;
                
                // Disable cursor blinking and set to underscore during typing
                term.options.cursorStyle = 'underline';
                term.options.cursorBlink = false;
                
                
                // Check if we should apply scrolling effect for this message
                if (typeof message === 'object' && message.scroll) {
                    // Get current terminal dimensions
                    const rows = term.rows;
                    
                    // Use all available rows (subtract 1 for the prompt line)
                    const spacerRows = Math.max(5, rows - 1);
                    
                    // Send newlines to create space
                    term.write('\n'.repeat(spacerRows));
                    
                    // Move cursor back up the same number of lines
                    term.write('\033[' + spacerRows + 'A');
                }
                
                // Use typewriter effect for the message text
                // If message is an object (JSON format), handle title and message separately
                if (typeof message === 'object') {
                    const { message: msgText, title, title_color, message_color, msg_src } = message;
                    
                    // ANSI color codes
                    const BOLD = "\x1b[1m";
                    const RESET = "\x1b[0m";
                    
                    // Handle title if provided
                    if (title) {
                        // Apply title color if provided

                        const titleColorCode = title_color ? colorToAnsi(title_color) : '';
                        
                        // Apply formatting codes directly
                        term.write('\r\n');
                        term.write(`${BOLD}${titleColorCode}${title}${RESET}`);
                        term.write('\r\n');

                    } else {
                        // Just add a newline for all messages without a title
                        term.write('\r\n');
                    }
                    await new Promise(resolve => setTimeout(resolve, 1));
                    
                    // Handle message with optional color
                    const messageColorCode = message_color ? colorToAnsi(message_color) : '';
                    if (messageColorCode) {
                        term.write(messageColorCode);
                    }
                    
                    // Use typewriter for message text
                    await typeWriter(msgText);
                    
                    // Reset formatting
                    if (messageColorCode) {
                        term.write(RESET);
                        await new Promise(resolve => setTimeout(resolve, 1));
                    }
                } else {
                    await typeWriter(message);
                }
                
                // Restore original cursor settings
                term.options.cursorStyle = originalCursorStyle;
                term.options.cursorBlink = originalCursorBlink;
                term.write('\r\n> ');
                
                // Ensure terminal has focus when displaying the prompt
                term.focus();
            }
            
            processingMessages = false;
            commandBuffer = '';
        }
        
        socket.onmessage = (event) => {
            try {
                // Stop the spinner when we receive a response
                stopSpinner();
                
                // Parse JSON message
                const jsonMessage = JSON.parse(event.data);
                
                // Debug message contents
                console.log("Received message:", jsonMessage);
                
                // Add the original message to the queue with all properties intact
                messageQueue.push(jsonMessage);
                
                // Start processing if not already doing so
                processMessageQueue();
            } catch (e) {
                console.error("Error parsing message:", e);
                // Fallback to displaying raw message if JSON parsing fails
                messageQueue.push(event.data);
                processMessageQueue();
            }
        };
        
        // Convert color string to ANSI code
        function colorToAnsi(color) {
            // Handle common color names
            const colorMap = {
                'black': "\x1b[30m",
                'red': "\x1b[31m",
                'green': "\x1b[32m",
                'yellow': "\x1b[33m",
                'blue': "\x1b[94m", // Using bright blue (94) instead of dark blue (34) for better visibility
                'magenta': "\x1b[35m",
                'cyan': "\x1b[36m",
                'white': "\x1b[37m"
            };
            
            if (color && colorMap[color.toLowerCase()]) {
                return colorMap[color.toLowerCase()];
            }
            
            // If it's a hex color, we can't directly convert to ANSI
            // We'll use approximate matching to basic colors for now
            if (color && color.startsWith('#')) {
                // For simplicity, return a default color
                // In a more advanced implementation, this could map hex to closest ANSI
                return "\x1b[37m"; // default to white
            }
            
            return ''; // Default - no color
        }
    }
    
    // Spinner animation
    let spinnerInterval = null;
    let spinnerTimeout = null;
    //const spinnerFrames = ['●∙∙∙', '∙●∙∙', '∙∙●∙', '∙∙∙●', '∙∙●∙', '∙●∙∙'];
    const spinnerFrames = ['●∙∙', '∙●∙', '∙∙●', '∙●∙'];
    let spinnerFrame = 0;
    
    function startSpinner() {
        // Clear any existing spinner
        stopSpinner();
        
        // Initialize spinner state
        spinnerFrame = 0;
        
        // Write initial frame inline without newline
        // Use cyan color for spinner (\x1b[36m)
        term.write('\x1b[36m' + spinnerFrames[0] + '\x1b[0m');
        
        // Start spinner animation
        spinnerInterval = setInterval(() => {
            spinnerFrame = (spinnerFrame + 1) % spinnerFrames.length;
            // Move cursor back 4 characters and write the next frame with same color
            term.write('\b\b\b\b\x1b[36m' + spinnerFrames[spinnerFrame]    + '\x1b[0m');
        }, 150); // Animation speed - adjust as needed
        
        // Set a timeout to stop the spinner after 30 seconds if no response
        spinnerTimeout = setTimeout(() => {
            stopSpinner();
            term.write('\r\n\x1b[31mNo response received.\x1b[0m\r\n> ');
        }, 30000); // 30 second timeout
    }
    
    function stopSpinner() {
        // Clear interval and timeout
        if (spinnerInterval) {
            clearInterval(spinnerInterval);
            spinnerInterval = null;
        }
        
        if (spinnerTimeout) {
            clearTimeout(spinnerTimeout);
            spinnerTimeout = null;
        }
        
        // Clear the spinner text by writing spaces over it
        // Need to account for the ANSI color codes when clearing
        term.write('\b\b\b\b\b\b\b\b\b\b          \r');
    }
    
    // Handle terminal input
    term.onKey(({ key, domEvent }) => {
        const printable = !domEvent.altKey && !domEvent.ctrlKey && !domEvent.metaKey;
        
        // Handle special keys
        if (domEvent.keyCode === 13) { // Enter key
            // Send command to server
            if (connected && commandBuffer.trim()) {
                term.write('\r\n');
                
                // Start spinner animation on the same line
                startSpinner();
                
                socket.send(commandBuffer);
                commandHistory.push(commandBuffer);
                historyPosition = commandHistory.length;
            } else {
                term.write('\r\n');
            }
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
    
    // Fetch world info for page title and header
    async function fetchWorldInfo() {
        try {
            const response = await fetch('/api/world-info');
            const data = await response.json();
            if (data.success && data.title) {
                // Update page title
                document.title = `${data.title} - LLM-MUD`;
                
                // Update header
                const headerTitle = document.querySelector('header h1');
                if (headerTitle) {
                    headerTitle.textContent = data.title;
                }
            }
        } catch (error) {
            console.error("Error fetching world info:", error);
        }
    }
    
    // Initialize with blank prompt
    term.write('> ');
    
    // Fetch world info on page load
    fetchWorldInfo();
    
    // Check if user is already logged in
    if (authToken && username) {
        userDisplay.textContent = username;
        logoutBtn.style.display = 'inline-block';
        connectWebSocket();
        
        // Ensure terminal has focus when connection is established
        term.focus();
    } else {
        // Show login modal
        authModal.classList.add('active');
        
        // Focus on the first input field in the login form
        setTimeout(() => {
            document.getElementById('login-username').focus();
        }, 100);
    }
});