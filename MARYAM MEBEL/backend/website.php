<?php
// MARYAM MEBEL - Website functionality in PHP
// This file handles the website backend, serving existing templates

// Configuration - load from environment variables or use defaults
define('DATA_DIR', $_ENV['DATA_DIR'] ?? (__DIR__ . '/data/'));
define('UPLOAD_DIR', $_ENV['UPLOAD_DIR'] ?? (__DIR__ . '/static/uploads/'));
define('TEMPLATES_DIR', $_ENV['TEMPLATES_DIR'] ?? (__DIR__ . '/templates/'));
define('ADMIN_USERNAME', getenv('ADMIN_USERNAME') ?: ($_ENV['ADMIN_USERNAME'] ?? 'admin'));
define('ADMIN_PASSWORD_HASH', getenv('ADMIN_PASSWORD_HASH') ?: ($_ENV['ADMIN_PASSWORD_HASH'] ?? password_hash('maryam2025', PASSWORD_DEFAULT)));

// Ensure required directories exist
if (!is_dir(DATA_DIR)) {
    mkdir(DATA_DIR, 0755, true);
}
if (!is_dir(UPLOAD_DIR)) {
    mkdir(UPLOAD_DIR, 0755, true);
}

// Utility functions
function loadJSON($filename) {
    $path = DATA_DIR . $filename;
    if (file_exists($path)) {
        $content = file_get_contents($path);
        // Handle git merge conflict markers if present
        $content = preg_replace('/<<<<<<< HEAD.*?=======.*?>>>>>>>.*?\n/s', '', $content);
        return json_decode($content, true) ?: [];
    }
    return [];
}

function saveJSON($filename, $data) {
    $path = DATA_DIR . $filename;
    return file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function sanitizeInput($data) {
    return htmlspecialchars(strip_tags(trim($data)));
}

function getProductsByCategory($category = 'all') {
    $products = loadJSON('products.json');
    if ($category === 'all') {
        return $products;
    }
    return array_filter($products, function($product) use ($category) {
        return $product['category'] === $category;
    });
}

function getProductBySlug($slug) {
    $products = loadJSON('products.json');
    foreach ($products as $product) {
        if ($product['slug'] === $slug) {
            return $product;
        }
    }
    return null;
}

function addMessage($name, $phone, $email, $message) {
    $messages = loadJSON('messages.json');
    
    $newMessage = [
        'id' => count($messages) + 1,
        'name' => $name,
        'phone' => $phone,
        'email' => $email,
        'message' => $message,
        'timestamp' => date('c'),
        'read' => false
    ];
    
    $messages[] = $newMessage;
    saveJSON('messages.json', $messages);
    
    // Also send to Telegram bot if database exists
    sendToTelegramBot($newMessage);
    
    return true;
}

function sendToTelegramBot($messageData) {
    // Path to the Telegram bot database
    $botDbPath = $_ENV['BOT_DB_PATH'] ?? (getenv('BOT_DB_PATH') ?: (__DIR__ . '/../maryam bot/support_bot.db'));
    
    if (!file_exists($botDbPath)) {
        // If database doesn't exist, just return
        return false;
    }
    
    try {
        $pdo = new PDO("sqlite:$botDbPath");
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        
        // Create a new ticket for the order
        $stmt = $pdo->prepare("INSERT INTO tickets (user_id, topic, status, created_at) VALUES (?, ?, ?, ?)");
        $stmt->execute([0, 'buyurtma', 'open', date('c')]);
        $ticketId = $pdo->lastInsertId();
        
        // Create message text
        $messageText = "📦 YANGI BUYURTMA\n\n";
        $messageText .= "Ism: " . ($messageData['name'] ?? 'Noma\'lum') . "\n";
        $messageText .= "Telefon: " . ($messageData['phone'] ?? 'Noma\'lum') . "\n";
        
        if (!empty($messageData['email'])) {
            $messageText .= "Email: " . $messageData['email'] . "\n";
        }
        
        if (!empty($messageData['product_name'])) {
            $messageText .= "Mahsulot: " . $messageData['product_name'] . "\n";
        }
        
        $messageText .= "\nXabar: " . ($messageData['message'] ?? '');
        
        // Insert the message
        $stmt = $pdo->prepare("INSERT INTO messages (ticket_id, sender_id, sender_name, message_text, sent_at) VALUES (?, ?, ?, ?, ?)");
        $stmt->execute([$ticketId, 0, "Mijoz", $messageText, date('c')]);
        
        return true;
    } catch (PDOException $e) {
        error_log("Error sending to Telegram bot: " . $e->getMessage());
        return false;
    }
}

// Handle different routes
$requestUri = $_SERVER['REQUEST_URI'];
$requestMethod = $_SERVER['REQUEST_METHOD'];

// Extract route from URI
$route = parse_url($requestUri, PHP_URL_PATH);
$route = trim($route, '/');

// Remove query parameters
$route = explode('?', $route)[0];

// Route handling
switch ($route) {
    case '':
    case 'index.php':
        // Homepage - serve the existing index.html template
        $products = array_slice(loadJSON('products.json'), 0, 2);
        
        // Load the base template and replace placeholders
        $template = file_get_contents(TEMPLATES_DIR . 'index.html');
        
        // Replace template variables with actual data
        $template = str_replace('{{ products }}', json_encode($products), $template);
        
        // Replace Flask-specific template syntax with PHP-generated content
        $template = str_replace('{% if products %}', '<?php if (!empty($products)): ?>', $template);
        $template = str_replace('{% for product in products[:4] %}', '<?php foreach (array_slice($products, 0, 4) as $index => $product): ?>', $template);
        $template = str_replace('{% endfor %}', '<?php endforeach; ?>', $template);
        $template = str_replace('{% else %}', '<?php else: ?>', $template);
        $template = str_replace('{% endif %}', '<?php endif; ?>', $template);
        
        // Replace URL functions
        $template = str_replace("url_for('main.collection')", "'/collection'", $template);
        $template = str_replace("url_for('main.index')", "'/'", $template);
        $template = str_replace("url_for('main.contact')", "'/contact'", $template);
        $template = str_replace("url_for('static', filename='", "'static/", $template);
        
        // Replace template variables
        $template = str_replace('{{ product.name }}', '<?php echo htmlspecialchars($product[\'name\']); ?>', $template);
        $template = str_replace('{{ product.slug }}', '<?php echo $product[\'slug\']; ?>', $template);
        $template = str_replace('{{ product.main_image }}', '<?php echo $product[\'main_image\']; ?>', $template);
        
        // Execute the PHP code in the template
        eval('?>' . $template);
        break;
    
    case 'collection':
        // Product collection page - serve the existing collection.html template
        $category = $_GET['category'] ?? 'all';
        $products = getProductsByCategory($category);
        
        // Check if template exists, otherwise create basic output
        $templatePath = TEMPLATES_DIR . 'collection.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            
            // Replace template variables
            $template = str_replace('{{ products }}', json_encode($products), $template);
            $template = str_replace('{{ category }}', $category, $template);
            
            // Replace Flask-specific template syntax
            $template = str_replace('{% if products %}', '<?php if (!empty($products)): ?>', $template);
            $template = str_replace('{% for product in products %}', '<?php foreach ($products as $product): ?>', $template);
            $template = str_replace('{% endfor %}', '<?php endforeach; ?>', $template);
            $template = str_replace('{% else %}', '<?php else: ?>', $template);
            $template = str_replace('{% endif %}', '<?php endif; ?>', $template);
            
            // Replace URL functions
            $template = str_replace("url_for('main.collection')", "'/collection'", $template);
            $template = str_replace("url_for('main.index')", "'/'", $template);
            $template = str_replace("url_for('main.contact')", "'/contact'", $template);
            $template = str_replace("url_for('static', filename='", "'static/", $template);
            $template = str_replace("url_for('product', product_name=product.slug)", "'/product/' . $product['slug']", $template);
            
            // Replace template variables
            $template = str_replace('{{ product.name }}', '<?php echo htmlspecialchars($product[\'name\']); ?>', $template);
            $template = str_replace('{{ product.slug }}', '<?php echo $product[\'slug\']; ?>', $template);
            $template = str_replace('{{ product.main_image }}', '<?php echo $product[\'main_image\']; ?>', $template);
            $template = str_replace('{{ product.description }}', '<?php echo htmlspecialchars($product[\'description\']); ?>', $template);
            
            eval('?>' . $template);
        } else {
            // Basic fallback template
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Collection - Maryam Furniture</title>
                <meta charset='UTF-8'>
                <link rel='stylesheet' href='static/css/main.css'>
            </head>
            <body>
                <h1>Product Collection</h1>
                <div class='container'>";
                
            foreach ($products as $product) {
                echo "<div class='product-card'>
                    <h3>" . htmlspecialchars($product['name']) . "</h3>
                    <p>" . htmlspecialchars($product['description']) . "</p>
                    <p>Price: " . number_format($product['price'], 0, '', ' ') . " UZS</p>
                    <a href='/product/{$product['slug']}'>View Details</a>
                </div>";
            }
            
            echo "</div>
            </body>
            </html>";
        }
        break;
    
    case 'contact':
        // Contact page - serve the existing contact.html template
        if ($requestMethod === 'POST') {
            $name = sanitizeInput($_POST['name'] ?? '');
            $phone = sanitizeInput($_POST['phone'] ?? '');
            $email = sanitizeInput($_POST['email'] ?? '');
            $message = sanitizeInput($_POST['message'] ?? '');
            $product_name = sanitizeInput($_POST['product_name'] ?? '');
            
            if (!empty($name) && !empty($phone) && !empty($message)) {
                // Add to messages
                $messageText = $message;
                if (!empty($product_name)) {
                    $messageText = "[MAHSULOT BUYURTMASI: $product_name]\n$message";
                }
                
                addMessage($name, $phone, $email, $messageText);
                
                // Redirect to success page
                header('Location: /contact_success');
                exit;
            }
        }
        
        $product_name = $_GET['product'] ?? '';
        
        // Check if template exists, otherwise create basic output
        $templatePath = TEMPLATES_DIR . 'contact.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            
            // Replace Flask-specific template syntax
            $template = str_replace("url_for('main.contact')", "'/contact'", $template);
            $template = str_replace("url_for('static', filename='", "'static/", $template);
            
            eval('?>' . $template);
        } else {
            // Basic fallback template
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Contact - Maryam Furniture</title>
                <meta charset='UTF-8'>
                <link rel='stylesheet' href='static/css/main.css'>
            </head>
            <body>
                <h1>Contact Us</h1>
                <form method='post' action='/contact'>
                    <div>
                        <label for='name'>Name:</label>
                        <input type='text' id='name' name='name' required>
                    </div>
                    <div>
                        <label for='phone'>Phone:</label>
                        <input type='tel' id='phone' name='phone' required>
                    </div>
                    <div>
                        <label for='email'>Email:</label>
                        <input type='email' id='email' name='email'>
                    </div>
                    <div>
                        <label for='message'>Message:</label>
                        <textarea id='message' name='message' required></textarea>
                    </div>
                    <button type='submit'>Send Message</button>
                </form>
            </body>
            </html>";
        }
        break;
    
    case 'contact_success':
        // Contact success page - serve the existing contact_success.html template
        $templatePath = TEMPLATES_DIR . 'contact_success.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            eval('?>' . $template);
        } else {
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Contact Success - Maryam Furniture</title>
                <meta charset='UTF-8'>
            </head>
            <body>
                <h1>Thank you for your message!</h1>
                <p>We will get back to you soon.</p>
                <a href='/'>Back to Home</a>
            </body>
            </html>";
        }
        break;
    
    case strpos($route, 'product/') === 0:
        // Product detail page
        $slug = substr($route, 8); // Remove 'product/' prefix
        $product = getProductBySlug($slug);
        
        if ($product) {
            // Check if template exists, otherwise create basic output
            $templatePath = TEMPLATES_DIR . 'product.html';
            if (file_exists($templatePath)) {
                $template = file_get_contents($templatePath);
                
                // Replace Flask-specific template syntax
                $template = str_replace("url_for('main.contact', product=product.name)", "'/contact?product={$product['name']}'", $template);
                $template = str_replace("url_for('static', filename='", "'static/", $template);
                
                // Replace product variables
                $template = str_replace('{{ product.name }}', htmlspecialchars($product['name']), $template);
                $template = str_replace('{{ product.description }}', htmlspecialchars($product['description']), $template);
                $template = str_replace('{{ product.price }}', number_format($product['price'], 0, '', ' '), $template);
                $template = str_replace('{{ product.main_image }}', $product['main_image'], $template);
                
                eval('?>' . $template);
            } else {
                echo "<!DOCTYPE html>
                <html>
                <head>
                    <title>{$product['name']} - Maryam Furniture</title>
                    <meta charset='UTF-8'>
                    <link rel='stylesheet' href='static/css/main.css'>
                </head>
                <body>
                    <h1>" . htmlspecialchars($product['name']) . "</h1>
                    <div class='product-detail'>
                        <img src='{$product['main_image']}' alt='" . htmlspecialchars($product['name']) . "'>
                        <div class='product-info'>
                            <p>" . htmlspecialchars($product['description']) . "</p>
                            <p>Price: " . number_format($product['price'], 0, '', ' ') . " UZS</p>
                            <p>Material: " . htmlspecialchars($product['material']) . "</p>
                            <p>Year: " . htmlspecialchars($product['year']) . "</p>
                            <p>Warranty: " . htmlspecialchars($product['warranty']) . "</p>
                            <a href='/contact?product=" . urlencode($product['name']) . "'>Order Now</a>
                        </div>
                    </div>
                </body>
                </html>";
            }
        } else {
            http_response_code(404);
            echo "<h1>Product not found</h1>";
        }
        break;
    
    case 'admin/login':
        // Admin login page
        $templatePath = TEMPLATES_DIR . 'admin/login.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            eval('?>' . $template);
        } else {
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Admin Login - Maryam Furniture</title>
                <meta charset='UTF-8'>
                <link rel='stylesheet' href='static/css/main.css'>
            </head>
            <body>
                <h1>Admin Login</h1>
                <form method='post' action='/admin/authenticate'>
                    <div>
                        <label for='username'>Username:</label>
                        <input type='text' id='username' name='username' required>
                    </div>
                    <div>
                        <label for='password'>Password:</label>
                        <input type='password' id='password' name='password' required>
                    </div>
                    <button type='submit'>Login</button>
                </form>
            </body>
            </html>";
        }
        break;
    
    case 'admin/authenticate':
        // Admin authentication
        if ($requestMethod === 'POST') {
            $username = sanitizeInput($_POST['username'] ?? '');
            $password = $_POST['password'] ?? '';
            
            // Check admin credentials using configured values
            if ($username === ADMIN_USERNAME && password_verify($password, ADMIN_PASSWORD_HASH)) {
                // For simplicity, we'll just set a session variable
                session_start();
                $_SESSION['admin_logged_in'] = true;
                header('Location: /admin/dashboard');
                exit;
            } else {
                // Redirect back to login with error
                header('Location: /admin/login?error=1');
                exit;
            }
        }
        break;
    
    case 'admin/dashboard':
        // Admin dashboard
        $products = loadJSON('products.json');
        $messages = loadJSON('messages.json');
        
        $templatePath = TEMPLATES_DIR . 'admin/dashboard.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            
            // Replace template variables
            $template = str_replace('{{ products|length }}', count($products), $template);
            $template = str_replace('{{ messages|length }}', count($messages), $template);
            
            eval('?>' . $template);
        } else {
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Admin Dashboard - Maryam Furniture</title>
                <meta charset='UTF-8'>
                <link rel='stylesheet' href='static/css/main.css'>
            </head>
            <body>
                <h1>Admin Dashboard</h1>
                <div class='admin-stats'>
                    <div class='stat-card'>
                        <h3>Products</h3>
                        <p>" . count($products) . "</p>
                    </div>
                    <div class='stat-card'>
                        <h3>Messages</h3>
                        <p>" . count($messages) . "</p>
                    </div>
                </div>
                <a href='/admin/new_product'>Add New Product</a>
                <a href='/admin/orders'>View Orders</a>
            </body>
            </html>";
        }
        break;
    
    case 'admin/new_product':
        // New product form
        if ($requestMethod === 'POST') {
            // Handle product creation
            $name = sanitizeInput($_POST['name'] ?? '');
            $description = sanitizeInput($_POST['description'] ?? '');
            $category = sanitizeInput($_POST['category'] ?? '');
            $material = sanitizeInput($_POST['material'] ?? '');
            $year = sanitizeInput($_POST['year'] ?? '');
            $warranty = sanitizeInput($_POST['warranty'] ?? '');
            $includes = sanitizeInput($_POST['includes'] ?? '');
            $price = (int)($_POST['price'] ?? 0);
            $discount = (int)($_POST['discount'] ?? 0);
            
            // Handle file upload
            $main_image = '';
            if (isset($_FILES['main_image']) && $_FILES['main_image']['error'] === UPLOAD_ERR_OK) {
                $uploadDir = UPLOAD_DIR;
                $fileName = time() . '_' . basename($_FILES['main_image']['name']);
                $uploadPath = $uploadDir . $fileName;
                
                if (move_uploaded_file($_FILES['main_image']['tmp_name'], $uploadPath)) {
                    $main_image = '/static/uploads/' . $fileName;
                }
            }
            
            // Create new product
            $newProduct = [
                'name' => $name,
                'slug' => strtolower(str_replace(' ', '-', $name)),
                'description' => $description,
                'category' => $category,
                'material' => $material,
                'year' => $year,
                'warranty' => $warranty,
                'includes' => $includes,
                'price' => $price,
                'discount' => $discount,
                'main_image' => $main_image,
                'gallery_images' => [],
                'created_at' => date('c'),
                'id' => uniqid(),
                'is_active' => true,
                'ratings' => []
            ];
            
            // Add to products
            $products = loadJSON('products.json');
            $products[] = $newProduct;
            saveJSON('products.json', $products);
            
            // Redirect to dashboard
            header('Location: /admin/dashboard');
            exit;
        }
        
        $templatePath = TEMPLATES_DIR . 'admin/new_product.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            eval('?>' . $template);
        } else {
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Add Product - Admin</title>
                <meta charset='UTF-8'>
                <link rel='stylesheet' href='static/css/main.css'>
            </head>
            <body>
                <h1>Add New Product</h1>
                <form method='post' action='/admin/new_product' enctype='multipart/form-data'>
                    <div>
                        <label for='name'>Product Name:</label>
                        <input type='text' id='name' name='name' required>
                    </div>
                    <div>
                        <label for='description'>Description:</label>
                        <textarea id='description' name='description' required></textarea>
                    </div>
                    <div>
                        <label for='category'>Category:</label>
                        <select id='category' name='category' required>
                            <option value='xonaki'>Xonaki</option>
                            <option value='ofis'>Ofis</option>
                            <option value='yotoqxona'>Yotoqxona</option>
                            <option value='oshxona'>Oshxona</option>
                        </select>
                    </div>
                    <div>
                        <label for='material'>Material:</label>
                        <input type='text' id='material' name='material' required>
                    </div>
                    <div>
                        <label for='year'>Year:</label>
                        <input type='text' id='year' name='year' required>
                    </div>
                    <div>
                        <label for='warranty'>Warranty:</label>
                        <input type='text' id='warranty' name='warranty' required>
                    </div>
                    <div>
                        <label for='includes'>Includes:</label>
                        <input type='text' id='includes' name='includes' required>
                    </div>
                    <div>
                        <label for='price'>Price:</label>
                        <input type='number' id='price' name='price' required>
                    </div>
                    <div>
                        <label for='discount'>Discount (%):</label>
                        <input type='number' id='discount' name='discount' value='0'>
                    </div>
                    <div>
                        <label for='main_image'>Main Image:</label>
                        <input type='file' id='main_image' name='main_image' accept='image/*'>
                    </div>
                    <button type='submit'>Add Product</button>
                </form>
            </body>
            </html>";
        }
        break;
    
    case 'admin/orders':
        // Admin orders page
        $messages = loadJSON('messages.json');
        
        $templatePath = TEMPLATES_DIR . 'admin/orders.html';
        if (file_exists($templatePath)) {
            $template = file_get_contents($templatePath);
            
            // Replace template variables
            $template = str_replace('{{ messages }}', json_encode($messages), $template);
            
            eval('?>' . $template);
        } else {
            echo "<!DOCTYPE html>
            <html>
            <head>
                <title>Orders - Admin</title>
                <meta charset='UTF-8'>
                <link rel='stylesheet' href='static/css/main.css'>
            </head>
            <body>
                <h1>Orders</h1>
                <div class='orders-list'>";
                
            foreach ($messages as $message) {
                echo "<div class='order-item'>
                    <h3>" . htmlspecialchars($message['name']) . "</h3>
                    <p><strong>Phone:</strong> " . htmlspecialchars($message['phone']) . "</p>
                    <p><strong>Email:</strong> " . htmlspecialchars($message['email']) . "</p>
                    <p><strong>Message:</strong> " . htmlspecialchars($message['message']) . "</p>
                    <p><strong>Date:</strong> " . $message['timestamp'] . "</p>
                </div>";
            }
            
            echo "</div>
            </body>
            </html>";
        }
        break;
    
    case 'static/':
        // Serve static files
        $filePath = __DIR__ . '/' . $route;
        if (file_exists($filePath)) {
            $mimeType = mime_content_type($filePath);
            header('Content-Type: ' . $mimeType);
            readfile($filePath);
            exit;
        } else {
            http_response_code(404);
            echo 'File not found';
        }
        break;
    
    default:
        // 404 for unmatched routes
        http_response_code(404);
        echo '<h1>404 - Page Not Found</h1>';
        break;
}