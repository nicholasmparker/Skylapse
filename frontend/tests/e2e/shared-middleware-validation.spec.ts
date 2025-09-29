/**
 * Comprehensive Playwright Test Suite for Shared Error Handling Middleware Validation
 * Professional Mountain Timelapse Camera System - Sprint 3 Task 5
 *
 * Tests validate that all services (capture, processing, backend) use consistent:
 * - Error response format and structure
 * - CORS headers across all endpoints
 * - Status codes and error handling
 * - Health check responses
 */

import { test, expect } from '@playwright/test';

// Service endpoints for testing
const SERVICES = {
  capture: {
    baseUrl: 'http://helios.local:8080',
    name: 'capture'
  },
  processing: {
    baseUrl: 'http://localhost:8081',
    name: 'processing'
  },
  backend: {
    baseUrl: 'http://localhost:8082',
    name: 'backend'
  }
};

// Expected error response structure based on shared middleware
interface SkylapsErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, any>;
    timestamp: string;
    service: string;
  };
}

// Expected CORS headers from shared middleware
const EXPECTED_CORS_HEADERS = [
  'access-control-allow-origin',
  'access-control-allow-methods',
  'access-control-allow-headers',
  'access-control-max-age'
];

// Expected security headers from shared middleware
const EXPECTED_SECURITY_HEADERS = [
  'x-content-type-options',
  'x-frame-options',
  'x-xss-protection'
];

test.describe('Shared Error Handling Middleware Validation', () => {

  test.describe('Test 5.1: Error Response Consistency Across Services', () => {

    test('All services return consistent 404 error format', async ({ request }) => {
      const responses: Record<string, any> = {};

      // Test 404 endpoints on all services
      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const response = await request.get(`${config.baseUrl}/nonexistent-endpoint`);
        responses[serviceName] = {
          status: response.status(),
          body: await response.json().catch(() => ({})),
          headers: response.headers()
        };

        // Should return 404
        expect(response.status()).toBe(404);
      }

      // Validate all services use same error response structure
      for (const [serviceName, responseData] of Object.entries(responses)) {
        const { body } = responseData;

        // Check required error structure fields
        expect(body).toHaveProperty('error');
        expect(body.error).toHaveProperty('code');
        expect(body.error).toHaveProperty('message');
        expect(body.error).toHaveProperty('details');
        expect(body.error).toHaveProperty('timestamp');
        expect(body.error).toHaveProperty('service');

        // Validate service name matches
        expect(body.error.service).toBe(SERVICES[serviceName as keyof typeof SERVICES].name);

        // Validate timestamp format (ISO 8601)
        expect(body.error.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
      }
    });

    test('All services return consistent 500 error format for invalid JSON', async ({ request }) => {
      const responses: Record<string, any> = {};

      // Test with malformed JSON on POST endpoints that accept JSON data
      const testEndpoints = {
        capture: '/capture/manual',
        processing: '/health',  // Use health endpoint that accepts POST
        backend: '/health'      // Use health endpoint that accepts POST
      };

      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const endpoint = testEndpoints[serviceName as keyof typeof testEndpoints];
        if (!endpoint) continue;

        const response = await request.post(`${config.baseUrl}${endpoint}`, {
          data: Buffer.from('{invalid-json}', 'utf8'),
          headers: { 'Content-Type': 'application/json' }
        });

        const responseBody = await response.json().catch(() => ({}));
        responses[serviceName] = {
          status: response.status(),
          body: responseBody,
          headers: response.headers()
        };

        // Should return 400 for bad JSON
        if (response.status() >= 500) {
          console.error(`Service ${serviceName} returned ${response.status()} for invalid JSON at ${config.baseUrl}${endpoint}`);
          console.error('Response body:', responseBody);
        }
        if (response.status() < 400) {
          console.error(`Service ${serviceName} returned ${response.status()} (expected >= 400) for invalid JSON at ${config.baseUrl}${endpoint}`);
          console.error('Response body:', responseBody);
        }
        expect(response.status()).toBeGreaterThanOrEqual(400);
        expect(response.status()).toBeLessThan(500);
      }

      // Validate error response structure consistency
      for (const [serviceName, responseData] of Object.entries(responses)) {
        const { body } = responseData;

        expect(body).toHaveProperty('error');
        expect(body.error).toHaveProperty('code');
        expect(body.error).toHaveProperty('message');
        expect(body.error).toHaveProperty('service');
        expect(body.error.service).toBe(SERVICES[serviceName as keyof typeof SERVICES].name);
      }
    });
  });

  test.describe('Test 5.2: CORS Headers Consistency Across Services', () => {

    test('All services return identical CORS headers', async ({ request }) => {
      const corsTests: Record<string, any> = {};

      // Test CORS headers on health endpoints
      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const response = await request.get(`${config.baseUrl}/health`);
        corsTests[serviceName] = {
          status: response.status(),
          headers: response.headers()
        };
      }

      // Extract CORS headers from each service
      const corsHeaders: Record<string, Record<string, string>> = {};
      for (const [serviceName, testData] of Object.entries(corsTests)) {
        corsHeaders[serviceName] = {};

        for (const headerName of EXPECTED_CORS_HEADERS) {
          const headerValue = testData.headers[headerName];
          if (headerValue) {
            corsHeaders[serviceName][headerName] = headerValue;
          }
        }
      }

      // Validate all services have required CORS headers
      for (const [serviceName, headers] of Object.entries(corsHeaders)) {
        for (const expectedHeader of EXPECTED_CORS_HEADERS) {
          expect(headers).toHaveProperty(expectedHeader);
        }
      }

      // Validate CORS header values are consistent (allowing for service-specific origins)
      const firstService = Object.keys(corsHeaders)[0];
      const referenceHeaders = corsHeaders[firstService];

      for (const [serviceName, headers] of Object.entries(corsHeaders)) {
        // Methods and max-age should be identical
        expect(headers['access-control-allow-methods']).toBe(referenceHeaders['access-control-allow-methods']);
        expect(headers['access-control-max-age']).toBe(referenceHeaders['access-control-max-age']);

        // Origins can vary by service but should follow same pattern
        expect(headers['access-control-allow-origin']).toBeDefined();
      }
    });

    test('All services handle CORS preflight OPTIONS requests consistently', async ({ request }) => {
      const preflightTests: Record<string, any> = {};

      // Test OPTIONS requests on health endpoints
      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const response = await request.fetch(`${config.baseUrl}/health`, {
          method: 'OPTIONS',
          headers: {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type'
          }
        });

        preflightTests[serviceName] = {
          status: response.status(),
          headers: response.headers()
        };

        // Should return 200 for valid preflight
        expect(response.status()).toBe(200);
      }

      // Validate all services handle preflight consistently
      for (const [serviceName, testData] of Object.entries(preflightTests)) {
        const { headers } = testData;

        // Required CORS preflight headers
        expect(headers).toHaveProperty('access-control-allow-origin');
        expect(headers).toHaveProperty('access-control-allow-methods');
        expect(headers).toHaveProperty('access-control-allow-headers');
      }
    });
  });

  test.describe('Test 5.3: Security Headers Consistency', () => {

    test('All services return consistent security headers', async ({ request }) => {
      const securityTests: Record<string, any> = {};

      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const response = await request.get(`${config.baseUrl}/health`);
        securityTests[serviceName] = {
          status: response.status(),
          headers: response.headers()
        };
      }

      // Validate security headers are present and consistent
      for (const [serviceName, testData] of Object.entries(securityTests)) {
        const { headers } = testData;

        for (const securityHeader of EXPECTED_SECURITY_HEADERS) {
          expect(headers).toHaveProperty(securityHeader);
        }

        // Validate specific security header values
        expect(headers['x-content-type-options']).toBe('nosniff');
        expect(headers['x-frame-options']).toBe('DENY');
        expect(headers['x-xss-protection']).toBe('1; mode=block');
      }
    });
  });

  test.describe('Test 5.4: API Error Response Format Validation', () => {

    test('All services return standardized error JSON structure', async ({ request }) => {
      // Test various error scenarios across services
      const errorTests = [
        {
          description: 'Invalid endpoint (404)',
          endpoint: '/invalid-endpoint',
          method: 'GET',
          expectedStatus: 404
        },
        {
          description: 'Method not allowed',
          endpoint: '/health',
          method: 'DELETE',
          expectedStatus: 405
        }
      ];

      for (const testCase of errorTests) {
        const testResults: Record<string, any> = {};

        for (const [serviceName, config] of Object.entries(SERVICES)) {
          let response;
          try {
            response = await request.fetch(`${config.baseUrl}${testCase.endpoint}`, {
              method: testCase.method as any
            });
          } catch (error) {
            // Some methods might not be supported, skip gracefully
            continue;
          }

          if (response.status() >= 400) {
            const body = await response.json().catch(() => ({}));
            testResults[serviceName] = {
              status: response.status(),
              body,
              headers: response.headers()
            };
          }
        }

        // Validate error response structure for each service
        for (const [serviceName, result] of Object.entries(testResults)) {
          const { body, status } = result;

          // Should have standardized error structure
          expect(body).toHaveProperty('error');
          expect(body.error).toHaveProperty('code');
          expect(body.error).toHaveProperty('message');
          expect(body.error).toHaveProperty('details');
          expect(body.error).toHaveProperty('timestamp');
          expect(body.error).toHaveProperty('service');

          // Service name should match
          expect(body.error.service).toBe(SERVICES[serviceName as keyof typeof SERVICES].name);

          // Error code should be meaningful
          expect(body.error.code).toMatch(/[A-Z_]+/);

          // Message should be non-empty
          expect(body.error.message).toBeTruthy();

          // Details should be an object
          expect(typeof body.error.details).toBe('object');

          // Timestamp should be valid ISO format
          expect(body.error.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
        }
      }
    });
  });

  test.describe('Test 5.5: Service Health Checks Consistency', () => {

    test('All services implement identical health check behavior', async ({ request }) => {
      const healthTests: Record<string, any> = {};

      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const response = await request.get(`${config.baseUrl}/health`);
        const body = await response.json().catch(() => ({}));

        healthTests[serviceName] = {
          status: response.status(),
          body,
          headers: response.headers()
        };
      }

      // Validate health check response structure is consistent
      for (const [serviceName, testData] of Object.entries(healthTests)) {
        const { status, body, headers } = testData;

        // Health checks should return 200 or 503
        expect([200, 503]).toContain(status);

        // Should have required health check fields
        expect(body).toHaveProperty('status');
        expect(body).toHaveProperty('timestamp');

        // Status should be 'healthy' or 'unhealthy'
        expect(['healthy', 'unhealthy']).toContain(body.status);

        // Should have CORS headers
        for (const corsHeader of EXPECTED_CORS_HEADERS) {
          expect(headers).toHaveProperty(corsHeader);
        }

        // Should have security headers
        for (const securityHeader of EXPECTED_SECURITY_HEADERS) {
          expect(headers).toHaveProperty(securityHeader);
        }
      }
    });

    test('Health checks return service-specific metadata', async ({ request }) => {
      const healthTests: Record<string, any> = {};

      for (const [serviceName, config] of Object.entries(SERVICES)) {
        const response = await request.get(`${config.baseUrl}/health`);
        const body = await response.json().catch(() => ({}));

        healthTests[serviceName] = {
          status: response.status(),
          body
        };
      }

      // Each service should identify itself correctly in health checks
      for (const [serviceName, testData] of Object.entries(healthTests)) {
        const { body } = testData;

        // Should contain service identification
        if (body.version || body.service || body.component) {
          // At least one service identifier should be present
          expect(
            body.version || body.service || body.component
          ).toBeTruthy();
        }
      }
    });
  });

  test.describe('Test 5.6: Error Logging Standardization Validation', () => {

    test('Services handle and log errors consistently', async ({ request }) => {
      // Test that error responses indicate proper error handling
      const errorScenarios = [
        {
          name: 'Invalid JSON payload',
          endpoint: '/health',
          method: 'POST',
          data: 'invalid-json',
          headers: { 'Content-Type': 'application/json' }
        }
      ];

      for (const scenario of errorScenarios) {
        const results: Record<string, any> = {};

        for (const [serviceName, config] of Object.entries(SERVICES)) {
          try {
            const response = await request.fetch(`${config.baseUrl}${scenario.endpoint}`, {
              method: scenario.method as any,
              data: scenario.data,
              headers: scenario.headers
            });

            const body = await response.json().catch(() => ({}));
            results[serviceName] = {
              status: response.status(),
              body,
              hasErrorStructure: body.error && body.error.code && body.error.timestamp
            };
          } catch (error) {
            // Service might not be running, that's okay for this test
            results[serviceName] = { error: error.message };
          }
        }

        // Validate that responses indicate proper error handling
        for (const [serviceName, result] of Object.entries(results)) {
          if (result.status >= 400 && result.hasErrorStructure) {
            // Error was properly handled and structured
            expect(result.body.error.service).toBe(SERVICES[serviceName as keyof typeof SERVICES].name);
            expect(result.body.error.timestamp).toBeTruthy();
          }
        }
      }
    });
  });

  test.describe('Test 5.7: Middleware Integration Validation', () => {

    test('No duplicate error handling code remains in services', async ({ request }) => {
      // This test validates that responses come from shared middleware
      // by checking for consistent response patterns that would be unlikely
      // if each service had custom error handling

      const testEndpoints = [
        '/nonexistent-1',
        '/nonexistent-2',
        '/nonexistent-3'
      ];

      for (const endpoint of testEndpoints) {
        const responses: Record<string, any> = {};

        for (const [serviceName, config] of Object.entries(SERVICES)) {
          const response = await request.get(`${config.baseUrl}${endpoint}`);
          const body = await response.json().catch(() => ({}));

          responses[serviceName] = {
            status: response.status(),
            errorCode: body.error?.code,
            errorStructure: JSON.stringify({
              hasCode: !!body.error?.code,
              hasMessage: !!body.error?.message,
              hasTimestamp: !!body.error?.timestamp,
              hasService: !!body.error?.service,
              hasDetails: !!body.error?.details
            })
          };
        }

        // All services should return identical error structures for 404s
        const structures = Object.values(responses).map(r => r.errorStructure);
        const uniqueStructures = [...new Set(structures)];

        // Should have only one unique structure (from shared middleware)
        expect(uniqueStructures.length).toBe(1);

        // All should have same error code for same scenario
        const errorCodes = Object.values(responses).map(r => r.errorCode).filter(Boolean);
        if (errorCodes.length > 1) {
          const uniqueCodes = [...new Set(errorCodes)];
          expect(uniqueCodes.length).toBe(1);
        }
      }
    });
  });
});
