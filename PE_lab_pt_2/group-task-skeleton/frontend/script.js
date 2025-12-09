document.addEventListener('DOMContentLoaded', () => {

    const apiEndpointSelector = document.getElementById('api-endpoint-selector');
    const callApiButton = document.getElementById('call-api-btn');
    const jsonOutputTextarea = document.getElementById('json-output');
    const statusMessageDiv = document.getElementById('status-message');

    callApiButton.addEventListener('click', handleCallApi);

    async function handleCallApi() {
        // Get the selected value from the dropdown
        const apiUrl = apiEndpointSelector.value.trim();

        if (!apiUrl) {
            displayStatus('Please select an API endpoint.', 'text-red-600');
            return;
        }

        // Clear previous output and status
        jsonOutputTextarea.value = '';
        displayStatus('Calling API...', 'text-blue-600');
        callApiButton.disabled = true; // Disable button during fetch

        try {
            const response = await fetch(apiUrl);

            if (!response.ok) {
                // Attempt to read error message from response body if available
                let errorMessage = `HTTP Error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    if (errorData.message) {
                        errorMessage += ` - ${errorData.message}`;
                    } else {
                        errorMessage += ` - ${JSON.stringify(errorData)}`;
                    }
                } catch (parseError) {
                    // If response is not JSON or empty, use default error message
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            jsonOutputTextarea.value = JSON.stringify(data, null, 2); // Pretty print JSON
            displayStatus('API call successful!', 'text-green-600');

        } catch (error) {
            console.error("Failed to call API:", error);
            jsonOutputTextarea.value = `Error: ${error.message}`;
            displayStatus(`Error calling API: ${error.message}`, 'text-red-600');
        } finally {
            callApiButton.disabled = false; // Re-enable button
        }
    }

    function displayStatus(message, colorClass) {
        statusMessageDiv.textContent = message;
        statusMessageDiv.className = `mt-4 text-center text-sm font-semibold ${colorClass}`;
    }
});
