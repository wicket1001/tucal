<?php

const JSON_FLAGS = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES;

/**
 * Uses random_bytes() to generate a cryptographically secure base58 token
 * @param int $len The length of the token to generate
 * @param null|string $table Optional name of the table to check against
 * @param string $column Optional name of the column to check against
 * @param bool $db_mode If true, use _DB
 * @return string Returns a cryptographically secure token with length $len
 * @throws Exception If no appropriate source of randomness can be found
 */
function generate_token(int $len, string $table = null, string $column = 'token', bool $db_mode = false): string {
    $ALPHA = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ';
    $MIN = 0;
    $MAX = strlen($ALPHA) - 1;

    if ($db_mode) {
        $stmt = ($table !== null) ? _db_prepare("SELECT COUNT(*) FROM $table WHERE $column = ?") : null;
    } else {
        $stmt = ($table !== null) ? db_prepare("SELECT COUNT(*) FROM $table WHERE $column = ?") : null;
    }

    do {
        $token = '';
        $bytes = random_bytes($len);
        $all = 0;
        for ($i = 0; $i < $len; $i++) {
            $all += ord($bytes[$i]);
            $token .= $ALPHA[$MIN + ($all % ($MAX - $MIN))];
        }

        if ($stmt !== null) {
            $stmt->execute([$token]);
            if ($stmt->fetchColumn() == 0)
                break;
        }
    } while ($stmt !== null);

    return $token;
}

function http_message(int $status): string {
    switch ($status) {
        case 400: return 'Bad Request';
        case 401: return 'Unauthorized';
        case 403: return 'Forbidden';
        case 404: return 'Not Found';
        case 409: return 'Conflict';
        case 410: return 'Gone';
        case 500: return 'Internal Server Error';
        case 501: return 'Not Implemented';
        default: return "$status";
    }
}

function force_user_login(string $location = null, bool $verified = true) {
    global $USER;
    if (!isset($USER) || ($verified && !$USER['verified'])) {
        $_SESSION['opts']['redirect'] = $location ?? $_SERVER['REQUEST_URI'];
        redirect(!isset($USER) ? '/account/login' : '/account/verify');
    }
}

function redirect(string $location, bool $tucal_exit = true) {
    // Use Necronda web server default error documents
    header("Status: 303");
    header("Location: $location");
    header("Content-Type: text/html");
    header("Content-Length: 0");
    header("Content-Security-Policy: default-src 'unsafe-inline' 'self' data:");
    if ($tucal_exit) {
        tucal_exit();
    } else {
        exit();
    }
}

function base32_decode(string $data): string {
    $alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    $data .= '========';
    $plain = '';
    for ($i = 0; $i < strlen($data); $i += 8) {
        $block = substr($data, $i, 8);
        if ($block[0] === '=') {
            break;
        }
        $val = 0;
        $min = 0;
        for ($j = 0; $j < 8; $j++) {
            $pos = strpos($alpha, $block[$j]);
            if ($pos === false) {
                if ($j <= 3) {
                    $min = 4;
                } elseif ($j <= 4) {
                    $min = 3;
                } elseif ($j <= 6) {
                    $min = 2;
                } elseif ($j <= 7) {
                    $min = 1;
                }
                break;
            }
            $val |= $pos << ((7 - $j) * 5);
        }
        for ($j = 4; $j >= $min; $j--) {
            $plain .= chr(($val >> ($j * 8)) & 0xFF);
        }
    }
    return $plain;
}

function echo_account($row, $uri = null) {
    echo "<a class=\"account\" data-username=\"$row[username]\" data-nickname=\"$row[nickname]\" data-mnr=\"$row[mnr]\"";
    if ($uri !== null) echo " href=\"$uri\"";

    echo '><div>';
    echo '<img src="/res/avatars/default.png" alt="' . _('Avatar') . '"/>';
    echo "<div>";
    echo "<span class=\"name\" contenteditable=\"true\">" . htmlspecialchars($row['nickname'] ?? $row['username']) . "</span>";
    echo '<div class="sub' . ($row['nickname'] ? ' has-nickname' : '') . '">';
    echo "<span class=\"mnr\">$row[mnr]</span>";
    echo "<span class=\"username\">$row[username]</span>";
    echo "</div></div></div></a>";
}

function echo_job(string $jobId, string $successUrl, string $errorUrl) {
    echo "<div class='job-viewer' data-job-id='$jobId'";

    $stmt = db_exec("SELECT data, status FROM tucal.v_job WHERE job_id = ?", [$jobId]);
    $rows = $stmt->fetchAll();
    if (sizeof($rows) === 0) {
        echo ' data-job-invalid="1"';
    } else {
        $data = json_decode($rows[0]['data'], true);
        $data['status'] = $rows[0]['status'];
    }

    echo ' data-success-href="' . htmlspecialchars($successUrl) . '"';
    echo ' data-error-href="' . htmlspecialchars($errorUrl) . '"';
    if (isset($data)) {
        echo ' data-job="' . htmlspecialchars(json_encode($data, JSON_FLAGS)) . '"';
    }
    echo '></div>';
}

function send_email(string $address, string $subject, string $msg, string $reply_to = null): bool {
    global $TUCAL;

    $msg .= "\n\n-- \n" .
        "This is an automatically generated and sent message.\n" .
        "If you did not take any action to receive such a message you may safely ignore this message.\n" .
        "For more information visit https://$TUCAL[hostname]/";

    $stmt = db_exec("
                INSERT INTO tucal.message (reply_to_address, to_address, subject, message)
                VALUES (:reply, :to, :subj, :msg)
                RETURNING message_nr", [
        'reply' => $reply_to,
        'to' => $address,
        'subj' => $subject,
        'msg' => $msg,
    ]);
    $nr = $stmt->fetchAll()[0][0];

    $stmt = db_prepare("SELECT send_ts FROM tucal.message WHERE message_nr = :nr");
    for ($i = 0; $i < 3; $i++) {
        sleep(1);
        $stmt->execute(['nr' => $nr]);
        $send = $stmt->fetchAll()[0][0];
        if ($send !== null)
            return true;
    }
    return false;
}
