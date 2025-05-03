# Database Configuration for MERL-T

MERL-T supports two database backends:

1. PostgreSQL (recommended for production use)
2. Mock Database (for development and testing)

## PostgreSQL Configuration

To use PostgreSQL (recommended for production environments):

1. Ensure you have a PostgreSQL server running (version 12 or higher recommended)
2. Create a database for MERL-T:

   ```bash
   createdb merl_t
   ```
3. Configure the PostgreSQL connection in `merl_t/config/defaults.yaml`:

   ```yaml
   # Database configuration
   database:
     type: "postgresql"  # Must be set to "postgresql" to enable PostgreSQL
     connection:
       host: "localhost"  # PostgreSQL server hostname
       port: 5432         # PostgreSQL server port
       user: "postgres"   # Database username
       password: "postgres" # Database password
       database: "merl_t"   # Database name
     pool:
       max_size: 10
       timeout: 30
   ```
4. Make sure all parameters in the `connection` section are properly configured.

## Mock Database Configuration

For development or if you don't have PostgreSQL available, MERL-T will automatically use a memory-based mock database implementation in these cases:

1. When the `database.type` setting is not set to "postgresql"
2. When PostgreSQL connection parameters are missing
3. When the connection to PostgreSQL fails

To explicitly use the mock database, set the database type to something other than "postgresql":

```yaml
# Database configuration
database:
  type: "mock"  # Set to any value other than "postgresql" to use mock database
  # ... other configuration options will be ignored
```

## How It Works

The application checks for PostgreSQL configuration on startup:

1. If PostgreSQL is properly configured and the connection succeeds, it will use the real PostgreSQL implementation
2. If PostgreSQL configuration is missing or the connection fails, it will automatically fall back to using the mock implementation

## Limitations of the Mock Database

The mock database implementation has the following limitations:

1. Data is stored in memory and lost when the application restarts
2. Only basic functionality is implemented
3. Default admin user with username "admin" and password "admin" is always available
4. Limited or no support for complex queries and filters
5. Not suitable for production use

## Troubleshooting

If you're having issues with the PostgreSQL connection:

1. Check that your PostgreSQL server is running
2. Verify credentials in the configuration file
3. Ensure the database exists and the user has appropriate permissions
4. Check the application logs for specific error messages
