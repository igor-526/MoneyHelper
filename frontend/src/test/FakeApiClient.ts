import { type ApiRequest, BaseApiClient } from "@/shared/api";

export type FakeHandler = (request: ApiRequest) => unknown | Promise<unknown>;

/** Фейковый `ApiClient` для тестов: ответ (или исключение) задаёт обработчик, сети нет. */
export class FakeApiClient extends BaseApiClient {
  readonly requests: ApiRequest[] = [];

  constructor(private readonly handler: FakeHandler) {
    super();
  }

  protected async request<T>(request: ApiRequest): Promise<T> {
    this.requests.push(request);
    return (await this.handler(request)) as T;
  }
}
