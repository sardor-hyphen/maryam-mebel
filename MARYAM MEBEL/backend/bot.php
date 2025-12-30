<?php
// MARYAM MEBEL - Telegram Bot functionality in PHP
// This file handles the Telegram bot functionality

// Configuration - load from environment variables or use defaults
define('BOT_TOKEN', getenv('BOT_TOKEN') ?: ($_ENV['BOT_TOKEN'] ?? '8068468848:AAG3bXB_r4a1zQVl2naRWjUZR-8pQHus_Zc'));
define('ADMIN_IDS', getenv('ADMIN_IDS') ? explode(',', getenv('ADMIN_IDS')) : [5559190705, 5399658464]);
define('EMPLOYER_ID', getenv('EMPLOYER_ID') ?: 5399658464);
define('BOT_DB_PATH', $_ENV['BOT_DB_PATH'] ?? (__DIR__ . '/maryam bot/support_bot.db'));

// Ensure required directories exist
$botDir = dirname(BOT_DB_PATH);
if (!is_dir($botDir)) {
    mkdir($botDir, 0755, true);
}

// Database setup for bot
function setupBotDatabase() {
    try {
        $pdo = new PDO("sqlite:" . BOT_DB_PATH);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        
        // Create tickets table if it doesn't exist
        $pdo->exec("CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT,
            updated_at TEXT
        )");
        
        // Create messages table if it doesn't exist
        $pdo->exec("CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            sender_id INTEGER,
            sender_name TEXT,
            message_text TEXT,
            sent_at TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        )");
        
        // Create users table if it doesn't exist
        $pdo->exec("CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )");
        
        return $pdo;
    } catch (PDOException $e) {
        error_log("Database setup error: " . $e->getMessage());
        return null;
    }
}

// Function to send message via Telegram Bot API
function sendTelegramMessage($chatId, $text, $replyMarkup = null) {
    $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/sendMessage";
    
    $data = [
        'chat_id' => $chatId,
        'text' => $text,
        'parse_mode' => 'HTML'
    ];
    
    if ($replyMarkup) {
        $data['reply_markup'] = $replyMarkup;
    }
    
    $options = [
        'http' => [
            'header' => "Content-type: application/x-www-form-urlencoded\r\n",
            'method' => 'POST',
            'content' => http_build_query($data)
        ]
    ];
    
    $context = stream_context_create($options);
    $result = file_get_contents($url, false, $context);
    
    return json_decode($result, true);
}

// Function to send message to admin
function sendToAdmin($text) {
    foreach (ADMIN_IDS as $adminId) {
        sendTelegramMessage($adminId, $text);
    }
}

// Function to get user info
function getUserInfo($userId) {
    $pdo = setupBotDatabase();
    if (!$pdo) return null;
    
    $stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");
    $stmt->execute([$userId]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

// Function to save/update user info
function saveUser($update) {
    $user = $update['message']['from'] ?? $update['callback_query']['from'] ?? null;
    if (!$user) return false;
    
    $pdo = setupBotDatabase();
    if (!$pdo) return false;
    
    $stmt = $pdo->prepare("INSERT OR REPLACE INTO users (
        id, username, first_name, last_name, language_code, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)");
    
    return $stmt->execute([
        $user['id'],
        $user['username'] ?? null,
        $user['first_name'] ?? null,
        $user['last_name'] ?? null,
        $user['language_code'] ?? null,
        date('c'),
        date('c')
    ]);
}

// Function to create a new ticket
function createTicket($userId, $topic) {
    $pdo = setupBotDatabase();
    if (!$pdo) return null;
    
    $stmt = $pdo->prepare("INSERT INTO tickets (user_id, topic, created_at, updated_at) VALUES (?, ?, ?, ?)");
    $result = $stmt->execute([$userId, $topic, date('c'), date('c')]);
    
    if ($result) {
        return $pdo->lastInsertId();
    }
    
    return null;
}

// Function to add message to ticket
function addMessageToTicket($ticketId, $senderId, $senderName, $messageText) {
    $pdo = setupBotDatabase();
    if (!$pdo) return false;
    
    $stmt = $pdo->prepare("INSERT INTO messages (ticket_id, sender_id, sender_name, message_text, sent_at) VALUES (?, ?, ?, ?, ?)");
    return $stmt->execute([$ticketId, $senderId, $senderName, $messageText, date('c')]);
}

// Function to get user's active ticket
function getUserTicket($userId) {
    $pdo = setupBotDatabase();
    if (!$pdo) return null;
    
    $stmt = $pdo->prepare("SELECT * FROM tickets WHERE user_id = ? AND status = 'open' ORDER BY created_at DESC LIMIT 1");
    $stmt->execute([$userId]);
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

// Main bot processing function
function processUpdate($update) {
    // Save user info
    saveUser($update);
    
    // Check if it's a message
    if (isset($update['message'])) {
        $message = $update['message'];
        $userId = $message['from']['id'];
        $text = $message['text'] ?? '';
        $chatId = $message['chat']['id'];
        
        // Handle commands
        if (strpos($text, '/') === 0) {
            switch ($text) {
                case '/start':
                    $response = "Assalomu alaykum! Maryam Mebel do'koniga xush kelibsiz. 🛋️\n\n" .
                               "Quyidagi bo'limlardan birini tanlang:";
                    
                    $keyboard = json_encode([
                        'keyboard' => [
                            [['text' => '✍️ Murojaat yuborish']],
                            [['text' => '📦 Buyurtma berish']],
                            [['text' => '📄 Vakansiyalar']],
                            [['text' => '💬 Mening chatlarim']],
                            [['text' => '📂 Katalog']]
                        ],
                        'resize_keyboard' => true
                    ]);
                    
                    sendTelegramMessage($chatId, $response, $keyboard);
                    break;
                
                case '/help':
                    $response = "Yordam:\n" .
                               "/start - Boshlash\n" .
                               "/help - Yordam olish\n" .
                               "Boshqa savollar uchun 'Murojaat yuborish' tugmasini bosing.";
                    sendTelegramMessage($chatId, $response);
                    break;
                
                default:
                    sendTelegramMessage($chatId, "Bunday komanda mavjud emas. /help orqali yordam oling.");
            }
        } else {
            // Handle text messages based on keyboard options
            switch ($text) {
                case '📦 Buyurtma berish':
                    $response = "Siz buyurtma berish bo'limidasiz.\n\n" .
                               "Iltimos, quyidagi ma'lumotlarni kiriting:\n" .
                               "1. Mahsulot nomi\n" .
                               "2. Miqdor\n" .
                               "3. Aloqa uchun telefon raqamingiz\n\n" .
                               "Yoki bekor qilish uchun 'Bekor qilish' deb yozing.";
                    sendTelegramMessage($chatId, $response);
                    break;
                
                case '✍️ Murojaat yuborish':
                    // Create a ticket for support
                    $ticketId = createTicket($userId, 'support');
                    if ($ticketId) {
                        $response = "Sizning murojaatingiz qabul qilindi. Tez orada siz bilan bog'lanamiz.\n" .
                                   "Murojaat raqami: #$ticketId\n\n" .
                                   "Endi murojaatingizni batafsil yozing:";
                        sendTelegramMessage($chatId, $response);
                        
                        // Add initial message
                        addMessageToTicket($ticketId, $userId, $message['from']['first_name'] ?? 'Foydalanuvchi', "Murojaat yuborish bo'limi tanlandi");
                    } else {
                        sendTelegramMessage($chatId, "Xatolik yuz berdi, iltimos qaytadan urinib ko'ring.");
                    }
                    break;
                
                case '📄 Vakansiyalar':
                    $response = "Vakansiyalar bo'limi hozirda ishlamoqda.\n\n" .
                               "Mavjud vakansiyalar:\n" .
                               "1. Mebel dizayneri\n" .
                               "2. Sotuvchi-konsultant\n" .
                               "3. Yig'uvchi-mehanik\n\n" .
                               "Qo'shimcha ma'lumot olish uchun 'Murojaat yuborish' bo'limidan murojaat yuboring.";
                    sendTelegramMessage($chatId, $response);
                    break;
                
                case '💬 Mening chatlarim':
                    // Get user's active ticket
                    $ticket = getUserTicket($userId);
                    if ($ticket) {
                        $response = "Sizning so'nggi murojaatingiz:\n" .
                                   "Raqami: #{$ticket['id']}\n" .
                                   "Mavzu: {$ticket['topic']}\n" .
                                   "Holati: {$ticket['status']}\n" .
                                   "Yaratilgan: {$ticket['created_at']}";
                        sendTelegramMessage($chatId, $response);
                    } else {
                        sendTelegramMessage($chatId, "Sizda hali faol murojaatingiz yo'q.");
                    }
                    break;
                
                case '📂 Katalog':
                    $response = "Katalog bo'limi hozirda ishlamoqda.\n\n" .
                               "Mahsulotlarimizni quyidagi havola orqali ko'rish mumkin:\n" .
                               "https://maryam-mebel.pythonanywhere.com/collection";
                    sendTelegramMessage($chatId, $response);
                    break;
                
                default:
                    // Check if user has an active ticket
                    $ticket = getUserTicket($userId);
                    if ($ticket) {
                        // Add message to existing ticket
                        $result = addMessageToTicket($ticket['id'], $userId, $message['from']['first_name'] ?? 'Foydalanuvchi', $text);
                        if ($result) {
                            // Notify admins about new message
                            $adminMessage = "Yangi xabar keldi:\n" .
                                          "Foydalanuvchi: " . ($message['from']['first_name'] ?? 'Noma\'lum') . " (@{$message['from']['username'] ?? 'Noma\'lum'})\n" .
                                          "Murojaat raqami: #{$ticket['id']}\n" .
                                          "Xabar: $text";
                            sendToAdmin($adminMessage);
                            
                            sendTelegramMessage($chatId, "Sizning xabaringiz qo'shildi. Tez orada javob olasiz.");
                        } else {
                            sendTelegramMessage($chatId, "Xatolik yuz berdi, iltimos qaytadan urinib ko'ring.");
                        }
                    } else {
                        // No active ticket, ask to select a category
                        $response = "Iltimos, quyidagi bo'limlardan birini tanlang:";
                        
                        $keyboard = json_encode([
                            'keyboard' => [
                                [['text' => '📦 Buyurtma berish']],
                                [['text' => '✍️ Murojaat yuborish']],
                                [['text' => '📄 Vakansiyalar']],
                                [['text' => '💬 Mening chatlarim']],
                                [['text' => '📂 Katalog']]
                            ],
                            'resize_keyboard' => true
                        ]);
                        
                        sendTelegramMessage($chatId, $response, $keyboard);
                    }
            }
        }
    }
    // Handle callback queries if needed
    elseif (isset($update['callback_query'])) {
        $callbackQuery = $update['callback_query'];
        $chatId = $callbackQuery['message']['chat']['id'];
        $data = $callbackQuery['data'];
        
        // Process callback data
        sendTelegramMessage($chatId, "Siz quyidagi tanlovni tanladingiz: $data");
    }
}

// Main function to run the bot
function runBot() {
    // Set up database
    $pdo = setupBotDatabase();
    if (!$pdo) {
        die("Database connection failed");
    }
    
    // Check if webhook is set up
    if (isset($_GET['setup_webhook'])) {
        $webhookUrl = (isset($_SERVER['HTTPS']) ? 'https' : 'http') . '://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
        $webhookUrl = str_replace('?setup_webhook=1', '', $webhookUrl);
        
        $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/setWebhook?url=" . urlencode($webhookUrl);
        $result = file_get_contents($url);
        $response = json_decode($result, true);
        
        if ($response['ok']) {
            echo "Webhook successfully set to: " . $webhookUrl;
        } else {
            echo "Failed to set webhook: " . $response['description'];
        }
        return;
    }
    
    // If it's a webhook request from Telegram
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $input = file_get_contents('php://input');
        $update = json_decode($input, true);
        
        if ($update) {
            processUpdate($update);
            // Return empty response to Telegram
            http_response_code(200);
            echo '';
            return;
        }
    }
    
    // If no webhook, this is likely a manual run or test
    echo "Telegram Bot is running.\n";
    echo "To set up webhook, visit: {$_SERVER['HTTP_HOST']}{$_SERVER['REQUEST_URI']}?setup_webhook=1\n";
}

// Run the bot
runBot();