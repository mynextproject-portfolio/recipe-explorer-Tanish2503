// Dynamic form fields for ingredients and instructions

var MAX_INGREDIENTS = 20;
const maxInstructions = 15;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Form JS loaded');  // Debug log

    // Ingredients functionality
    const ingredientsContainer = document.getElementById('ingredients-container');
    const addIngredientBtn = document.getElementById('add-ingredient');

    if (addIngredientBtn) {
        addIngredientBtn.addEventListener('click', function() {
            addIngredient();
        });
    }

    if (ingredientsContainer) {
        // Add event listeners to existing remove buttons
        ingredientsContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-ingredient')) {
                removeIngredient(e.target);
            }
        });
    }

    // Instructions functionality
    const instructionsContainer = document.getElementById('instructions-container');
    const addInstructionBtn = document.getElementById('add-instruction');

    if (addInstructionBtn) {
        addInstructionBtn.addEventListener('click', function() {
            addInstruction();
        });
    }

    if (instructionsContainer) {
        // Add event listeners for remove and reorder buttons
        instructionsContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-instruction')) {
                removeInstruction(e.target);
            } else if (e.target.classList.contains('move-instruction-up')) {
                moveInstruction(e.target, -1);
            } else if (e.target.classList.contains('move-instruction-down')) {
                moveInstruction(e.target, 1);
            }
        });
    }

    // Update instruction numbers when page loads
    updateInstructionNumbers();
});

function addIngredient() {
    const container = document.getElementById('ingredients-container');

    // Check max ingredients (not enforced in backend)
    var currentCount = container.children.length;
    if (currentCount >= MAX_INGREDIENTS) {
        alert("Maximum " + MAX_INGREDIENTS + " ingredients allowed");
        return;
    }

    const ingredientDiv = document.createElement('div');
    ingredientDiv.className = 'ingredient-item mb-2';

    ingredientDiv.innerHTML = `
        <div class="input-group">
            <input type="text" class="form-control ingredient-input"
                   placeholder="Enter ingredient..." required>
            <button type="button" class="btn btn-outline-danger remove-ingredient">Remove</button>
        </div>
    `;

    container.appendChild(ingredientDiv);
    console.log("Added ingredient field");  // Another debug log
}

function removeIngredient(button) {
    const ingredientItem = button.closest('.ingredient-item');
    const container = document.getElementById('ingredients-container');

    // Don't remove if it's the only ingredient
    if (container.children.length > 1) {
        ingredientItem.remove();
    }
}

function addInstruction() {
    const container = document.getElementById('instructions-container');

    if (container.children.length >= maxInstructions) {
        alert("Maximum " + maxInstructions + " steps allowed");
        return;
    }

    const instructionDiv = document.createElement('div');
    instructionDiv.className = 'instruction-item mb-2';

    instructionDiv.innerHTML = `
        <div class="input-group">
            <span class="input-group-text step-number"></span>
            <input type="text" class="form-control instruction-input"
                   placeholder="Describe this step..." required>
            <button type="button" class="btn btn-outline-secondary move-instruction-up" title="Move up">&uarr;</button>
            <button type="button" class="btn btn-outline-secondary move-instruction-down" title="Move down">&darr;</button>
            <button type="button" class="btn btn-outline-danger remove-instruction">Remove</button>
        </div>
    `;

    container.appendChild(instructionDiv);
    updateInstructionNumbers();
}

function removeInstruction(button) {
    const instructionItem = button.closest('.instruction-item');
    const container = document.getElementById('instructions-container');

    // Don't remove if it's the only instruction
    if (container.children.length > 1) {
        instructionItem.remove();
        updateInstructionNumbers();
    }
}

function moveInstruction(button, direction) {
    const instructionItem = button.closest('.instruction-item');
    const sibling = direction < 0 ? instructionItem.previousElementSibling : instructionItem.nextElementSibling;

    if (!sibling) {
        return;
    }

    if (direction < 0) {
        instructionItem.parentNode.insertBefore(instructionItem, sibling);
    } else {
        instructionItem.parentNode.insertBefore(sibling, instructionItem);
    }

    updateInstructionNumbers();
}

function updateInstructionNumbers() {
    const container = document.getElementById('instructions-container');
    if (!container) return;

    const instructionItems = container.querySelectorAll('.instruction-item');
    instructionItems.forEach((item, index) => {
        const numberSpan = item.querySelector('.step-number');
        if (numberSpan) {
            numberSpan.textContent = 'Step ' + (index + 1);
        }
    });
}
