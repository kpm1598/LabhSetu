
// LABHSETU FRONTEND INTERACTIONS

const toast = document.getElementById("toast");

let toastTimer;

function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

// MOBILE NAVIGATION

const menuToggle = document.getElementById("menuToggle");
const navLinks = document.getElementById("navLinks");

menuToggle.addEventListener("click", () => {
    navLinks.classList.toggle("show");
});

document.querySelectorAll(".nav-links a").forEach(link => {
    link.addEventListener("click", () => {
        navLinks.classList.remove("show");
    });
});

// ACTIVE NAVIGATION

const sections = document.querySelectorAll("main section[id]");

const navObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            document.querySelectorAll(".nav-links a").forEach(link => {
                link.classList.remove("active");

                if (link.getAttribute("href") === "#" + entry.target.id) {
                    link.classList.add("active");
                }
            });
        }
    });
}, { threshold: 0.3 });

sections.forEach(section => navObserver.observe(section));

// SCROLL ANIMATIONS

const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            revealObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.12 });

document.querySelectorAll(".reveal").forEach(element => {
    revealObserver.observe(element);
});

// SCHEME SEARCH - API NOT CONNECTED YET

document.getElementById("searchBtn").addEventListener("click", () => {
    const search = document.getElementById("schemeSearch").value.trim();
    const category = document.getElementById("categoryFilter").value;

    if (!search && !category) {
        showToast("Please enter a scheme keyword or select a category.");
        return;
    }

    showToast("Scheme database API is not connected yet.");
});

// DOCUMENT VALIDATION

const documentInput = document.getElementById("documentInput");

documentInput.addEventListener("change", () => {
    const file = documentInput.files[0];
    const status = document.getElementById("fileStatus");

    if (!file) return;

    const allowedTypes = [
        "application/pdf",
        "image/jpeg",
        "image/png"
    ];

    if (!allowedTypes.includes(file.type)) {
        documentInput.value = "";
        status.textContent = "Unsupported file type.";
        showToast("Please select a PDF, JPG or PNG file.");
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        documentInput.value = "";
        status.textContent = "File is larger than 5 MB.";
        showToast("Please select a file smaller than 5 MB.");
        return;
    }

    status.textContent = "Selected: " + file.name;
    showToast("Document selected successfully. Upload API pending.");
});

// SCHEME VERIFICATION

document.getElementById("verifySchemeBtn").addEventListener("click", () => {
    const value = document.getElementById("schemeVerifyInput").value.trim();

    if (!value) {
        showToast("Please enter a scheme name.");
        return;
    }

    document.getElementById("schemeVerifyStatus").textContent =
        "Verification API is not connected. No verification result is available.";

    showToast("Connect the verification API to check this scheme.");
});

// WEBSITE VERIFICATION

document.getElementById("verifyWebsiteBtn").addEventListener("click", () => {
    const value = document.getElementById("websiteInput").value.trim();

    if (!value) {
        showToast("Please enter a website address.");
        return;
    }

    try {
        const url = new URL(value);

        if (!["http:", "https:"].includes(url.protocol)) {
            throw new Error("Invalid protocol");
        }

        document.getElementById("websiteStatus").textContent =
            "Website entered. Authenticity check is awaiting backend integration.";

        showToast("Website submitted for future verification integration.");

    } catch {
        showToast("Please enter a valid HTTP or HTTPS URL.");
    }
});

// BENEFIT CALCULATOR - ESTIMATE ONLY

document.getElementById("calculateBtn").addEventListener("click", () => {
    const amount = Number(document.getElementById("benefitAmount").value);
    const months = Number(document.getElementById("benefitMonths").value);
    const result = document.getElementById("calculationResult");

    if (
        !Number.isFinite(amount) ||
        !Number.isFinite(months) ||
        amount <= 0 ||
        months <= 0 ||
        months > 120
    ) {
        showToast("Enter a positive monthly amount and 1–120 months.");
        return;
    }

    const total = amount * months;

    result.textContent =
        "Illustrative estimate: ₹" +
        total.toLocaleString("en-IN") +
        ". This is not a confirmed government entitlement.";

});

// NOTIFICATION TRANSLATOR

document.getElementById("translateBtn").addEventListener("click", () => {
    const text = document.getElementById("notificationText").value.trim();
    const language = document.getElementById("languageSelect").value;

    if (!text) {
        showToast("Please paste a government notification first.");
        return;
    }

    document.getElementById("translationStatus").textContent =
        "Text prepared for " + language +
        ". Translation API is awaiting backend integration.";

    showToast("Translation service is not connected yet.");
});

// APPLICATION READINESS CHECKLIST

const checks = document.querySelectorAll(".ready-check");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");

function updateProgress() {
    const completed = [...checks].filter(check => check.checked).length;
    const total = checks.length;

    const percentage = (completed / total) * 100;

    progressBar.style.width = percentage + "%";

    progressText.textContent =
        completed + " of " + total + " checklist items ready";

    if (completed === total) {
        showToast("Your demo checklist is complete!");
    }
}

checks.forEach(check => {
    check.addEventListener("change", updateProgress);
});

// KEYBOARD SEARCH

document.getElementById("schemeSearch").addEventListener("keydown", event => {
    if (event.key === "Enter") {
        document.getElementById("searchBtn").click();
    }
});
