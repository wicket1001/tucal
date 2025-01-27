<?php

global $STATUS;
global $ERROR;
global $TITLE;
global $LOCALE;
global $TUCAL;

if (!isset($STATUS)) {
    require "main.php";
}

header("Cache-Control: private, no-cache");
header("Content-Security-Policy: default-src https://$TUCAL[hostname]");
header("Referrer-Policy: same-origin");
header("Strict-Transport-Security: max-age=15768000");  // 6 months
header("X-Content-Type-Options: nosniff");
header("X-Frame-Options: SAMEORIGIN");
header("X-XSS-Protection: 1; mode=block");

function uri_active(string $uri, bool $exact = false): string {
    if ($exact) {
        return $_SERVER['REQUEST_URI'] === $uri ? 'active' : '';
    } else {
        return substr($_SERVER['REQUEST_URI'], 0, strlen($uri)) === $uri ? 'active' : '';
    }
}

$cal_uri = isset($USER) ? "/calendar/$USER[mnr]/" : "/calendar/";

$icon = "tucal";

if ($STATUS >= 400 && $STATUS < 600) {
    $msg = http_message($STATUS);
    $TITLE = ["$STATUS " . _ctx('http', $msg)];
    $icon = "tp";  // "Technische Probleme Wien" Easter Egg
}

?>
<!DOCTYPE html>
<html lang="<?php
    echo $LOCALE;
?>" data-status="<?php
    echo $STATUS;
?>" data-mnr="<?php
    if (isset($USER)) echo $USER['mnr'];
?>" class="<?php
    if (isset($_SESSION['opts']['theme'])) {
        $theme = $_SESSION['opts']['theme'];
        echo "theme-$theme";
    } else {
        echo "theme-browser";
    }
?>">
<head>
    <title><?php
        $TITLE = $TITLE ?? [];
        $TITLE[] = 'TUcal';
        echo htmlspecialchars(implode(' - ', $TITLE));
    ?></title>
    <meta charset="UTF-8"/>
    <meta name="author" content="Lorenz Stechauner"/>
    <meta name="robots" content="notranslate"/>
    <meta name="description" content=""/>
    <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
    <meta name="user-options" content="<?php echo isset($USER) ? htmlspecialchars(json_encode($USER['opts'])) : '{}';?>"/>
    <meta name="theme-color" content="#4080C0"/>
    <meta name="color-scheme" content="<?php if (isset($theme)) {if ($theme == 'light') echo "light"; else echo "dark";} else {echo "light dark";}?>"/>
    <meta name="apple-mobile-web-app-capable" content="yes"/>
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>
    <link rel="stylesheet" href="/res/styles/styles.css" type="text/css"/>
    <link rel="icon" href="/res/svgs/<?php echo $icon;?>.svg" type="image/svg+xml" sizes="any"/>
    <link rel="icon" href="/favicon.ico" type="image/x-icon" sizes="256x256 128x128 64x64 32x32 24x24 16x16"/>
    <link rel="manifest" href="/app.webmanifest"/>
    <script src="/res/scripts/min.js" type="application/javascript"></script>
</head>
<body>
<nav>
    <div id="nav-left">
        <div id="nav-home">
            <a href="/" class="<?php echo uri_active('/', true);?>">
                <img src="/res/svgs/<?php echo $icon;?>.svg" alt="<?php echo _('Home');?>"/>
            </a>
        </div>
    </div>
    <div id="nav-center">
        <div class="link" id="nav-home-explicit"><a href="/" class="<?php echo uri_active('/', true);?>"><?php echo _('Home');?></a></div>
        <div class="link"><a href="<?php echo $cal_uri;?>" class="<?php echo uri_active($cal_uri);?>"><?php echo _('My Calendar');?></a></div>
        <div class="link"><a href="/friends/" class="<?php echo uri_active('/friends/', true);?>"><?php echo _('My Friends');?></a></div>
        <div class="link"><a href="/courses/" class="<?php echo uri_active('/courses/');?>"><?php echo _('My Courses');?></a></div>
    </div>
    <div id="nav-right">
        <div id="nav-live">
            <a href="" class="button live" target="_blank">LIVE<span></span></a>
            <a href="" class="button live" target="_blank">LIVE<span></span></a>
            <a href="" class="button live" target="_blank">LIVE<span></span></a>
        </div>
        <div id="nav-user">
<?php if (isset($USER)) { ?>
            <div id="user-menu">
                <div>
                    <img src="/res/avatars/default.png" alt="<?php echo _('Avatar');?>"/>
                    <a><?php echo $USER['username'];?></a>
                    <span class="arrow">▾</span>
                </div>
                <div><a href="/account/"><?php echo _('Settings');?></a></div>
                <?php if (!$USER['verified']) { ?><div><a href="/account/verify"><?php echo _('Verify account');?></a></div><?php }
                else { ?><div><a href="/account/sync"><?php echo _('Sync TU account');?></a></div><?php }?>

                <hr/>
                <div><a href="/search"><?php echo _('Search (for)');?></a></div>
                <hr/>
                <div>
                    <form action="/account/logout" method="post" name="logout"></form>
                    <a href="/account/logout"><?php echo _('Logout');?></a>
                </div>
            </div>
<?php } else { ?>
            <a href="/account/sign-up" class="button <?php echo uri_active('/account/sign-up', true);?>"><?php echo _('Sign up');?></a>
            <a href="/account/login" class="button <?php echo uri_active('/account/login', true);?>"><?php echo _('Login');?></a>
<?php } ?>
        </div>
    </div>
</nav>
<div class="wrapper">
<?php  if ($STATUS >= 400 && $STATUS < 600) {
    $msg = http_message($STATUS); ?>
    <main class="w1">
        <section class="status error">
            <h1><?php echo $STATUS;?></h1>
            <h2><?php echo _ctx('http', $msg)?> :&#xFEFF;(</h2>
            <p><?php echo _ctx('http', "${msg} (description)")?></p>
            <p><?php echo htmlspecialchars($ERROR)?></p>
        </section>
    </main>
<?php
    require "footer.php";
}
