async function checkPiResponse() {
  try {
    const response = await fetch("/get_pi_response");
    const data = await response.json();
    if (data.signal) {
      $("#server-response").text(data.message);
      $(".container").hide();
      $("#success-box").css("display", "block");
      $(".reload-btn1").css('display', 'inline-block');
    }
    else if (data.signal==false){
      $("#server-response").text(data.message);
      $(".container").hide();
      $("#success-box").css("color", "rgb(255, 68, 0)");
      $("#success-box").css("background-color", "rgb(224, 144, 144)");
      $("#success-box").css("border", "1px solid rgb(212, 103, 103)");
      $(".reload-btn1").css("background-color", "rgb(252, 6, 6)");
      $("#success-box").css("display", "block");
      $(".reload-btn1").css('display', 'inline-block');

    }
  } catch (error) {
    console.error("Error checking Pi response:", error);
  }
}

function reload() {
  location.reload();
}

function closeWarning() {
  $("#warning-box").hide();
  $(".container").show();
  location.reload();
}

const FULL_DASH_ARRAY = 565.48;
const TIME_LIMIT = 60;
let timePassed = 0;
let timeLeft = TIME_LIMIT;
let timerInterval = null;

const progressCircle = document.getElementById("progressCircle");
const timerText = document.getElementById("timerText");

function interpolateColor(color1, color2, factor) {
  const c1 = color1.match(/\d+/g).map(Number);
  const c2 = color2.match(/\d+/g).map(Number);
  return `rgb(${c1.map((c, i) => Math.round(c + factor * (c2[i] - c))).join(",")})`;
}

function hexToRgb(hex) {
  const bigint = parseInt(hex.slice(1), 16);
  return `rgb(${(bigint >> 16) & 255}, ${(bigint >> 8) & 255}, ${bigint & 255})`;
}

const green = hexToRgb("#22c55e");
const yellow = hexToRgb("#eab308");
const red = hexToRgb("#ef4444");

function getColorForTimeLeft(timeLeft) {
  if (timeLeft > TIME_LIMIT / 2) {
    const factor = 1 - (timeLeft - TIME_LIMIT / 2) / (TIME_LIMIT / 2);
    return interpolateColor(green, yellow, factor);
  } else {
    const factor = 1 - timeLeft / (TIME_LIMIT / 2);
    return interpolateColor(yellow, red, factor);
  }
}

function calculateTimeFraction() {
  return timeLeft / TIME_LIMIT;
}

function setCircleDashoffset() {
  const offset = FULL_DASH_ARRAY * (1 - calculateTimeFraction());
  progressCircle.style.strokeDashoffset = offset;
}

function updateTimer() {
  timePassed += 1;
  timeLeft = TIME_LIMIT - timePassed;
  timerText.textContent = timeLeft > 0 ? timeLeft : 0;
  setCircleDashoffset();
  progressCircle.style.stroke = getColorForTimeLeft(timeLeft > 0 ? timeLeft : 0);

  if (timeLeft <= 0) {
    clearInterval(timerInterval);
    window.location.href = "/search_page";
  }
}

function startTimer() {
  timePassed = 0;
  timeLeft = TIME_LIMIT;
  progressCircle.style.strokeDashoffset = 0;
  progressCircle.style.stroke = green;
  timerInterval = setInterval(updateTimer, 1000);
  setInterval(checkPiResponse, 3000);
}

$(document).ready(function () {
  $("#warning-box").hide();
  $("#success-box").hide();

  $("#search-form").on("submit", function (e) {
    e.preventDefault();
    const voterId = $("#voter_id").val();

    $.ajax({
      url: "/search_page",
      method: "POST",
      data: { voter_id: voterId },
      success: function (response) {
        try {
          if (response.vote_status !== "Voter already Voted") {
          $("#voter-name").text(response.name);
          $("#voter-voter-id").text(response.voterId);
          $("#voter-state").text(response.state);
          $("#voter-district").text(response.district);
          $("#voter-constitution").text(response.constitution);
          $("#voter-gender").text(response.gender);
          $("#voter-dob").text(response.date_of_birth);
          $("#voter-area").text(response.area);

          if (response.photo_base64) {
            $("#voter-photo").attr("src", "data:image/jpeg;base64," + response.photo_base64);
          } else {
            $("#voter-photo").attr("src", "");
          }

          $("#voter-modal").css("display", "flex");
        } else {
          $(".container").hide();
          $("#warning-box").show();
        }
        } catch (error) {
          alert(error)
        }
        
      },
      error: function () {
        alert("Voter not found!");
      }
    });
  });

  $(".close-button").on("click", function () {
    $("#voter-modal").hide();
  });

  $("#confirm-button").on("click", function () {
    $(".container").hide();
    $("#voter-modal").hide();
    $("#timer-box").css("display", "flex");
    startTimer();
  });
});

function checkSession() {
  fetch("/check_session")
    .then(response => response.json())
    .then(data => {
      if (!data.active) {
        alert("Session expired! Closing tab...");
        window.location.href = "/logout";
        window.open('', '_self', '');
        window.close();
      }
    });
}

setInterval(checkSession, 10000);
setInterval(() => location.reload(true), 75000);
setInterval(() => {
  fetch("/heartbeat", { method: "POST" });
}, 5000);

const ua = navigator.userAgent;
const isEdge = ua.includes("Edg/") || ua.includes("Edge/");
if (!isEdge) {
  document.body.innerHTML = "<h1 style='text-align:center; margin-top:20%; color:red;'>❌ Please use Microsoft Edge to access this website.</h1>";
  document.body.style.backgroundColor = "#f0f0f0";
  document.title = "Access Denied";
}
