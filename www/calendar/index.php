<?php

global $TITLE;
global $USER;
global $CONFIG;
global $USE_PATH_INFO;
global $STATUS;

require "../.php/session.php";
force_user_login();

$parts = explode('/', $_SERVER['PATH_INFO']);

$ref = time();
$ref = strtotime((4 - date('N', $ref)) . ' day', $ref);
$year = date('Y', $ref);
$week = 'W' . (int) date('W', $ref);

if (sizeof($parts) < 2 || strlen($parts[1]) === 0)
    redirect("/calendar/$USER[mnr]/$year/$week/");

$subject = $parts[1];
if (sizeof($parts) < 3 || strlen($parts[2]) === 0)
    redirect("/calendar/$subject/$year/$week/");

$year = $parts[2];
if (sizeof($parts) < 5 || strlen($parts[3]) === 0)
    redirect("/calendar/$subject/$year/$week/");

$unit = $parts[3];

if (sizeof($parts) !== 5) {
    $STATUS = 404;
}

if (strlen($year) === 4 && is_numeric($year)) {
    $year = (string) (int) $year;
} else {
    $STATUS = 404;
}

if ($unit[0] === 'W' || $unit[0] === 'w') {
    $week = (int) substr($unit, 1);
    if ($week >= 1 && $week <= 53) {
        $unit = "W$week";
    } else {
        $STATUS = 404;
    }
} elseif (is_numeric($unit)) {
    $month = (int) $unit;
    if ($month >= 1 && $month <= 12) {
        $unit = (string) $month;
    } else {
        $STATUS = 404;
    }
} else {
    $STATUS = 404;
}

$USE_PATH_INFO = true;
require "../.php/main.php";

$wanted_uri = "/calendar/$subject/$year/$unit/$parts[4]";
if ($_SERVER['REQUEST_URI'] !== $wanted_uri) {
    redirect($wanted_uri);
}

$TITLE = [];

if ($subject === $USER['mnr']) {
    $TITLE[] = _('My Calendar');
} else {
    $stmt = db_exec("
            SELECT a.username, f1.nickname
            FROM tucal.friend f1
                JOIN tucal.v_account a ON a.account_nr = f1.account_nr_1
            WHERE (a.mnr, f1.account_nr_2) = (:mnr, :nr)", [
        'mnr' => $subject,
        'nr' => $USER['nr'],
    ]);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if (sizeof($rows) === 0) {
        $STATUS = 403;
    } else {
        $TITLE[] = htmlspecialchars($rows[0]['nickname'] ?? $rows[0]['username']);
    }
    $TITLE[] = _('Calendar');
}


if (!isset($STATUS) || $STATUS === 200) {
    $stmt = db_exec("SELECT * FROM tucal.calendar_export WHERE account_nr = :nr", ['nr' => $USER['nr']]);
}

require "../.php/header.php";
?>
<main class="wcal">
    <!--Calendar-->
    <section class="calendar-legend">
        <div class="legend lecture">
            <div></div>
            <span class="color-name"><?php echo _('Blue');?></span>
            <span><?php echo _('Lecture');?></span>
        </div>
        <div class="legend course">
            <div></div>
            <span class="color-name"><?php echo _('Purple');?></span>
            <span><?php echo _('General course event');?></span>
        </div>
        <div class="legend group">
            <div></div>
            <span class="color-name"><?php echo _('Green');?></span>
            <span><?php echo _('Group event');?></span>
        </div>
        <div class="legend other">
            <div></div>
            <span class="color-name"><?php echo _('Grey');?></span>
            <span><?php echo _('Other event');?></span>
        </div>
        <div class="legend online">
            <div></div>
            <span class="color-name"><?php echo _('Striped');?></span>
            <span><?php echo _('Online-only event');?></span>
        </div>
    </section>
    <section>
        <h2><?php echo _('Calendar exports');?></h2>
        <table class="calendar-exports">
            <thead>
                <tr><th>Name</th><th>Link</th><th>Settings</th><th></th></tr>
            </thead>
            <tbody>
<?php

while ($row = $stmt->fetch()) {
    echo "<tr>";
    echo "<td>$row[subject_mnr]</td>";
    $path = "/calendar/export/$row[token]/personal.ics";
    echo "<td><a href='$path' class='copy-link'>" . _("Open link") . "</a></td>";
    echo "<td></td>";
    echo "<td><form action='/calendar/export/remove?id=$row[export_id]' method='post'><button type='submit'>" . _('Remove') . "</button></form></td>";
    echo "</tr>\n";
}

?>
            </tbody>
        </table>
        <form action="/calendar/export/add?subject=<?php echo htmlspecialchars($subject);?>" method="post">
            <button type="submit"><?php echo _('Export calendar');?></button>
        </form>
    </section>
</main>
<?php
require "../.php/footer.php";
